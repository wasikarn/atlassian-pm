"""ADF Validator — Quality Gate enforcement for Jira ADF documents.

Validates ADF JSON against templates.md + verification-checklist.md rules.
Supports: Story, Subtask, Epic, QA, Task issue types.
Scoring: pass=1, warn=0.5, fail=0. Overall >=90% = pass.

Usage (via scripts/validate_adf.py):
    python validate_adf.py tasks/story.json --type story
    python validate_adf.py tasks/story.json --type story --fix
"""

import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

VALID_PANEL_TYPES = frozenset({"info", "success", "warning", "error", "note"})
VALID_ISSUE_TYPES = frozenset({"story", "subtask", "epic", "qa", "task"})
SUBTASK_TAGS = ("[BE]", "[FE-Admin]", "[FE-Web]", "[QA]")
QG_THRESHOLD = 90.0

# Regex patterns
FILE_PATH_RE = re.compile(r"(?:[\w@.-]+/){1,}[\w@.-]+\.\w{1,6}")
API_ROUTE_RE = re.compile(r"/api/[\w/.-]+")
COMPONENT_RE = re.compile(
    r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+"
    r"(?:Page|Component|Service|Controller|Module|Guard|Hook|Provider|Store|Repository|Model|DTO)\b"
)
THAI_RE = re.compile(r"[\u0E00-\u0E7F]")
NARRATIVE_AS_RE = re.compile(r"As a\s", re.IGNORECASE)
NARRATIVE_WANT_RE = re.compile(r"I want\s", re.IGNORECASE)
NARRATIVE_SO_RE = re.compile(r"So that\s", re.IGNORECASE)
GIVEN_RE = re.compile(r"Given[:\s]", re.IGNORECASE)
WHEN_RE = re.compile(r"When[:\s]", re.IGNORECASE)
THEN_RE = re.compile(r"Then[:\s]", re.IGNORECASE)
GENERIC_PERSONA_RE = re.compile(r"As a user[,.\s]", re.IGNORECASE)


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════


class CheckStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    check_id: str
    status: CheckStatus
    message: str
    fix_hint: str = ""
    auto_fixable: bool = False


@dataclass
class ValidationReport:
    issue_type: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        if not self.checks:
            return 0.0
        total = sum(
            1.0 if c.status == CheckStatus.PASS else 0.5 if c.status == CheckStatus.WARN else 0.0 for c in self.checks
        )
        return total / len(self.checks) * 100

    @property
    def passed(self) -> bool:
        return self.score >= QG_THRESHOLD

    def to_dict(self) -> dict[str, Any]:
        counts = {"pass": 0, "warn": 0, "fail": 0}
        for c in self.checks:
            counts[c.status.value] += 1
        return {
            "issue_type": self.issue_type,
            "score": round(self.score, 1),
            "status": "pass" if self.score >= 90 else "warn" if self.score >= 70 else "fail",
            "total_checks": len(self.checks),
            "passed": counts["pass"],
            "warned": counts["warn"],
            "failed": counts["fail"],
            "issues": [
                {
                    "id": c.check_id,
                    "status": c.status.value,
                    "message": c.message,
                    "fix_hint": c.fix_hint,
                }
                for c in self.checks
                if c.status != CheckStatus.PASS
            ],
        }


# ═══════════════════════════════════════════════════════════
# ADF Utilities
# ═══════════════════════════════════════════════════════════


def walk_adf(node: Any, visitor: Callable[[dict], None]) -> None:
    """Walk ADF tree, calling visitor on each dict node.

    Only traverses 'content' arrays (the tree structure).
    Does NOT walk into 'attrs' (config) or 'marks' (styling).
    """
    if isinstance(node, dict):
        visitor(node)
        content = node.get("content")
        if isinstance(content, list):
            walk_adf(content, visitor)
    elif isinstance(node, list):
        for item in node:
            walk_adf(item, visitor)


def find_adf_nodes(node: Any, predicate: Callable[[dict], bool]) -> list[dict]:
    """Find all ADF nodes matching predicate."""
    results: list[dict] = []

    def _visitor(n: dict) -> None:
        if predicate(n):
            results.append(n)

    walk_adf(node, _visitor)
    return results


def extract_text(node: Any) -> str:
    """Extract all text content from an ADF subtree."""
    texts: list[str] = []

    def _visitor(n: dict) -> None:
        if n.get("type") == "text" and "text" in n:
            texts.append(n["text"])

    walk_adf(node, _visitor)
    return " ".join(texts)


def find_headings(adf: dict, level: int | None = None) -> list[dict]:
    """Find all heading nodes, optionally filtered by level."""
    return find_adf_nodes(
        adf,
        lambda n: n.get("type") == "heading" and (level is None or n.get("attrs", {}).get("level") == level),
    )


def get_section_content(adf: dict, heading_pattern: str) -> list[dict]:
    """Get content nodes between a heading matching pattern and the next same-level heading."""
    content = adf.get("content", [])
    section: list[dict] = []
    in_section = False
    section_level = None
    pattern_lower = heading_pattern.lower()

    for node in content:
        if node.get("type") == "heading":
            heading_text = extract_text(node).lower()
            if not in_section and pattern_lower in heading_text:
                in_section = True
                section_level = node.get("attrs", {}).get("level", 2)
                continue
            elif in_section:
                node_level = node.get("attrs", {}).get("level", 2)
                if node_level <= section_level:
                    break
        if in_section:
            section.append(node)

    return section


def has_code_mark(text_node: dict) -> bool:
    """Check if a text node has a code mark."""
    return any(m.get("type") == "code" for m in text_node.get("marks", []))


def has_link_mark(text_node: dict) -> bool:
    """Check if a text node has a link mark."""
    return any(m.get("type") == "link" for m in text_node.get("marks", []))


def detect_format(data: dict) -> tuple[str, dict]:
    """Detect JSON format and extract ADF document.

    Returns:
        Tuple of (format_type, adf) where format_type is "create", "edit", or "raw".
    """
    if data.get("type") == "doc":
        return "raw", data
    if "projectKey" in data:
        return "create", data.get("description", {})
    if "issues" in data:
        return "edit", data.get("description", {})
    if "description" in data:
        return "unknown", data.get("description", {})
    return "unknown", data


# ═══════════════════════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════════════════════


class AdfValidator:
    """Validate ADF documents against quality gate criteria.

    Checks by issue type:
        Story:   T1-T5 (technical) + S1-S6 (quality)  = 11 checks
        Subtask: T1-T5 (technical) + ST1-ST5 (quality) = 10 checks
        Epic:    T1-T5 (technical) + E1-E4 (quality)   = 9 checks
        QA:      T1-T5 (technical) + QA1-QA5 (quality) = 10 checks
        Task:    T1-T5 (technical) + TK1-TK4 (quality) = 9 checks
    """

    def validate(
        self,
        adf: dict,
        issue_type: str,
        wrapper: dict | None = None,
    ) -> ValidationReport:
        """Run all applicable checks for the issue type."""
        report = ValidationReport(issue_type=issue_type)

        # Technical checks (all types)
        report.checks.append(self._check_t1_adf_format(adf))
        report.checks.append(self._check_t2_panels(adf))
        report.checks.append(self._check_t3_inline_code(adf))
        report.checks.append(self._check_t4_links(adf, issue_type))
        report.checks.append(self._check_t5_required_fields(adf, issue_type, wrapper))

        # Type-specific quality checks
        quality_map: dict[str, list[Callable]] = {
            "story": [
                lambda: self._check_s1_invest(adf),
                lambda: self._check_s2_narrative(adf),
                lambda: self._check_s3_anti_patterns(adf),
                lambda: self._check_s4_acceptance_criteria(adf),
                lambda: self._check_s5_scope(adf),
                lambda: self._check_s6_language(adf),
            ],
            "subtask": [
                lambda: self._check_st1_objective(adf),
                lambda: self._check_st2_scope_files(adf),
                lambda: self._check_st3_acceptance_criteria(adf),
                lambda: self._check_st4_tag_summary(adf, wrapper),
                lambda: self._check_st5_language(adf),
            ],
            "epic": [
                lambda: self._check_e1_vision(adf),
                lambda: self._check_e2_rice(adf),
                lambda: self._check_e3_scope(adf),
                lambda: self._check_e4_stories(adf),
            ],
            "qa": [
                lambda: self._check_qa1_coverage(adf),
                lambda: self._check_qa2_test_format(adf),
                lambda: self._check_qa3_scenarios(adf),
                lambda: self._check_qa4_test_data(adf),
                lambda: self._check_qa5_language(adf),
            ],
            "task": [
                lambda: self._check_tk1_context(adf),
                lambda: self._check_tk2_actionable(adf),
                lambda: self._check_tk3_acceptance(adf),
                lambda: self._check_tk4_language(adf),
            ],
        }

        for check_fn in quality_map.get(issue_type, []):
            report.checks.append(check_fn())

        return report

    def auto_fix(self, adf: dict, report: ValidationReport) -> tuple[dict, ValidationReport]:
        """Apply auto-fixes for fixable issues, return fixed ADF and new report."""
        fixed = deepcopy(adf)
        applied = []

        for check in report.checks:
            if not check.auto_fixable or check.status == CheckStatus.PASS:
                continue
            if check.check_id == "T2":
                self._fix_panel_types(fixed)
                applied.append("T2")
            elif check.check_id == "T3":
                self._fix_code_marks(fixed)
                applied.append("T3")

        new_report = self.validate(fixed, report.issue_type)
        return fixed, new_report

    # ───────────────────────────────────────────────────────
    # Technical Checks (T1–T5)
    # ───────────────────────────────────────────────────────

    def _check_t1_adf_format(self, adf: dict) -> CheckResult:
        """T1: ADF root structure — type: doc, version: 1, content array."""
        if adf.get("type") != "doc":
            return CheckResult("T1", CheckStatus.FAIL, 'Missing type: "doc"')
        if adf.get("version") != 1:
            return CheckResult("T1", CheckStatus.FAIL, "Missing version: 1")
        content = adf.get("content")
        if not isinstance(content, list) or len(content) == 0:
            return CheckResult("T1", CheckStatus.FAIL, "Content array empty or missing")
        return CheckResult("T1", CheckStatus.PASS, "Valid ADF structure")

    def _check_t2_panels(self, adf: dict) -> CheckResult:
        """T2: Panel structure — valid panelType, no nested tables."""
        panels = find_adf_nodes(adf, lambda n: n.get("type") == "panel")
        if not panels:
            return CheckResult("T2", CheckStatus.WARN, "No panels found in document")

        invalid_types = []
        nested_tables = 0
        for panel in panels:
            pt = panel.get("attrs", {}).get("panelType")
            if pt not in VALID_PANEL_TYPES:
                invalid_types.append(pt)
            # Check for tables inside panels
            tables = find_adf_nodes(panel, lambda n: n.get("type") == "table")
            nested_tables += len(tables)

        if invalid_types:
            return CheckResult(
                "T2",
                CheckStatus.FAIL,
                f"Invalid panelType: {invalid_types}",
                fix_hint="Change to one of: info, success, warning, error, note",
                auto_fixable=True,
            )
        if nested_tables:
            return CheckResult(
                "T2",
                CheckStatus.WARN,
                f"{nested_tables} table(s) nested inside panels — use bulletList instead",
            )
        return CheckResult("T2", CheckStatus.PASS, f"{len(panels)} panels OK")

    def _check_t3_inline_code(self, adf: dict) -> CheckResult:
        """T3: Inline code marks — file paths, API routes, component names."""
        unmarked: list[str] = []

        def _check_text(node: dict) -> None:
            if node.get("type") != "text" or "text" not in node:
                return
            if has_code_mark(node) or has_link_mark(node):
                return
            text = node["text"]
            if FILE_PATH_RE.search(text) or API_ROUTE_RE.search(text) or COMPONENT_RE.search(text):
                unmarked.append(text[:60])

        walk_adf(adf, _check_text)

        if not unmarked:
            return CheckResult("T3", CheckStatus.PASS, "Code marks OK")
        if len(unmarked) <= 2:
            return CheckResult(
                "T3",
                CheckStatus.WARN,
                f"{len(unmarked)} text(s) missing code marks: {unmarked[0]}",
                fix_hint="Add code marks to file paths and technical terms",
                auto_fixable=True,
            )
        return CheckResult(
            "T3",
            CheckStatus.FAIL,
            f"{len(unmarked)} text(s) missing code marks",
            fix_hint="Add code marks to file paths, API routes, component names",
            auto_fixable=True,
        )

    def _check_t4_links(self, adf: dict, issue_type: str) -> CheckResult:
        """T4: Links — reference section exists with links."""
        # Find link marks or inlineCard nodes
        links = find_adf_nodes(
            adf,
            lambda n: n.get("type") == "inlineCard" or (n.get("type") == "text" and has_link_mark(n)),
        )
        ref_section = get_section_content(adf, "reference")

        if issue_type in ("subtask", "story") and not ref_section and not links:
            return CheckResult(
                "T4",
                CheckStatus.WARN,
                "No Reference section or links found",
                fix_hint="Add Reference table with parent/Epic links",
            )
        if links or ref_section:
            return CheckResult("T4", CheckStatus.PASS, f"{len(links)} link(s) found")
        return CheckResult("T4", CheckStatus.PASS, "Links check N/A for this type")

    def _check_t5_required_fields(self, adf: dict, issue_type: str, wrapper: dict | None) -> CheckResult:
        """T5: Required fields in wrapper JSON."""
        if not wrapper:
            # Raw ADF — can only check description not empty
            if not adf.get("content"):
                return CheckResult("T5", CheckStatus.FAIL, "Description is empty")
            return CheckResult("T5", CheckStatus.PASS, "ADF content present (no wrapper)")

        fmt, _ = detect_format(wrapper)
        if fmt == "create":
            missing = []
            for f in ("projectKey", "type", "summary", "description"):
                if f not in wrapper:
                    missing.append(f)
            if missing:
                return CheckResult("T5", CheckStatus.FAIL, f"CREATE missing: {missing}")
            return CheckResult("T5", CheckStatus.PASS, "CREATE fields OK")
        elif fmt == "edit":
            missing = []
            for f in ("issues", "description"):
                if f not in wrapper:
                    missing.append(f)
            # Check forbidden fields
            forbidden = [f for f in ("projectKey", "type", "summary", "parent") if f in wrapper]
            if forbidden:
                return CheckResult(
                    "T5",
                    CheckStatus.FAIL,
                    f"EDIT has forbidden fields: {forbidden}",
                )
            if missing:
                return CheckResult("T5", CheckStatus.FAIL, f"EDIT missing: {missing}")
            return CheckResult("T5", CheckStatus.PASS, "EDIT fields OK")

        return CheckResult("T5", CheckStatus.WARN, f"Unknown wrapper format: {fmt}")

    # ───────────────────────────────────────────────────────
    # Story Quality Checks (S1–S6)
    # ───────────────────────────────────────────────────────

    def _check_s1_invest(self, adf: dict) -> CheckResult:
        """S1: INVEST — Small (<=5 AC panels), Testable (GWT in ACs)."""
        ac_section = get_section_content(adf, "acceptance criteria")
        ac_panels = [n for n in ac_section if n.get("type") == "panel"]

        if not ac_panels:
            return CheckResult("S1", CheckStatus.FAIL, "No AC panels found — not testable")
        if len(ac_panels) > 5:
            return CheckResult(
                "S1",
                CheckStatus.WARN,
                f"{len(ac_panels)} AC panels (>5) — consider splitting with SPIDR",
            )
        # Check testability: at least one panel has Given/When/Then
        testable = 0
        for panel in ac_panels:
            text = extract_text(panel)
            if GIVEN_RE.search(text) and WHEN_RE.search(text) and THEN_RE.search(text):
                testable += 1
        if testable == 0:
            return CheckResult(
                "S1",
                CheckStatus.FAIL,
                "No AC panels have Given/When/Then — not testable",
            )
        if testable < len(ac_panels):
            return CheckResult(
                "S1",
                CheckStatus.WARN,
                f"{testable}/{len(ac_panels)} ACs have Given/When/Then",
            )
        return CheckResult("S1", CheckStatus.PASS, f"INVEST OK ({len(ac_panels)} ACs, all testable)")

    def _check_s2_narrative(self, adf: dict) -> CheckResult:
        """S2: User Story narrative — As a / I want / So that."""
        story_section = get_section_content(adf, "user story")
        if not story_section:
            story_section = get_section_content(adf, "narrative")
        if not story_section:
            # Try first info panel as fallback
            panels = find_adf_nodes(
                adf,
                lambda n: n.get("type") == "panel" and n.get("attrs", {}).get("panelType") == "info",
            )
            story_section = panels[:1] if panels else []

        if not story_section:
            return CheckResult("S2", CheckStatus.FAIL, "No User Story narrative found")

        text = extract_text(story_section)
        has_as = bool(NARRATIVE_AS_RE.search(text))
        has_want = bool(NARRATIVE_WANT_RE.search(text))
        has_so = bool(NARRATIVE_SO_RE.search(text))

        missing = []
        if not has_as:
            missing.append('"As a [persona]"')
        if not has_want:
            missing.append('"I want to [action]"')
        if not has_so:
            missing.append('"So that [benefit]"')

        if not missing:
            return CheckResult("S2", CheckStatus.PASS, "Narrative format OK")
        if len(missing) <= 1:
            return CheckResult("S2", CheckStatus.WARN, f"Narrative missing: {missing[0]}")
        return CheckResult("S2", CheckStatus.FAIL, f"Narrative missing: {', '.join(missing)}")

    def _check_s3_anti_patterns(self, adf: dict) -> CheckResult:
        """S3: Narrative anti-patterns — generic persona, solution masking, missing why."""
        story_section = get_section_content(adf, "user story")
        if not story_section:
            story_section = get_section_content(adf, "narrative")
        text = extract_text(story_section) if story_section else ""

        if not text:
            return CheckResult("S3", CheckStatus.WARN, "No narrative text to check")

        issues: list[str] = []

        # Generic persona check
        if GENERIC_PERSONA_RE.search(text):
            issues.append("Generic persona: 'As a user' — specify role + situation")

        # Missing why: "So that" followed by very short text or restated goal
        so_match = NARRATIVE_SO_RE.search(text)
        if so_match:
            so_text = text[so_match.end() :].strip()
            # If benefit is less than 10 chars, likely too vague
            if len(so_text) < 10:
                issues.append("Missing why: 'So that' benefit too short")

        if not issues:
            return CheckResult("S3", CheckStatus.PASS, "No anti-patterns detected")
        if len(issues) == 1:
            return CheckResult("S3", CheckStatus.WARN, issues[0])
        return CheckResult("S3", CheckStatus.FAIL, f"{len(issues)} anti-patterns: {'; '.join(issues)}")

    def _check_s4_acceptance_criteria(self, adf: dict) -> CheckResult:
        """S4: AC format — panels with Given/When/Then, correct panel types."""
        ac_section = get_section_content(adf, "acceptance criteria")
        panels = [n for n in ac_section if n.get("type") == "panel"]

        if not panels:
            return CheckResult("S4", CheckStatus.FAIL, "No AC panels found")

        gwt_count = 0
        wrong_type = 0
        for panel in panels:
            pt = panel.get("attrs", {}).get("panelType", "")
            if pt not in ("success", "warning", "error"):
                wrong_type += 1
            text = extract_text(panel)
            if GIVEN_RE.search(text) and WHEN_RE.search(text) and THEN_RE.search(text):
                gwt_count += 1

        issues: list[str] = []
        if gwt_count < len(panels):
            issues.append(f"{len(panels) - gwt_count}/{len(panels)} ACs missing Given/When/Then")
        if wrong_type:
            issues.append(f"{wrong_type} AC panels with non-standard panelType")

        if not issues:
            return CheckResult("S4", CheckStatus.PASS, f"{len(panels)} ACs all correct")
        if gwt_count == 0:
            return CheckResult("S4", CheckStatus.FAIL, "; ".join(issues))
        return CheckResult("S4", CheckStatus.WARN, "; ".join(issues))

    def _check_s5_scope(self, adf: dict) -> CheckResult:
        """S5: Scope definition — services impacted, in/out scope."""
        scope_section = get_section_content(adf, "scope")
        text = extract_text(scope_section) if scope_section else ""

        if not scope_section:
            # Some stories use different heading names
            full_text = extract_text(adf)
            if "scope" in full_text.lower() or "service" in full_text.lower():
                return CheckResult("S5", CheckStatus.WARN, "Scope mentioned but no dedicated section")
            return CheckResult("S5", CheckStatus.WARN, "No Scope section found")

        if len(text.split()) < 5:
            return CheckResult("S5", CheckStatus.WARN, "Scope section too brief")
        return CheckResult("S5", CheckStatus.PASS, "Scope section present")

    def _check_s6_language(self, adf: dict) -> CheckResult:
        """S6: Language — Thai content with English technical terms."""
        return self._check_language("S6", adf)

    # ───────────────────────────────────────────────────────
    # Subtask Quality Checks (ST1–ST5)
    # ───────────────────────────────────────────────────────

    def _check_st1_objective(self, adf: dict) -> CheckResult:
        """ST1: Clear 1-2 sentence objective."""
        obj_section = get_section_content(adf, "objective")
        if not obj_section:
            return CheckResult("ST1", CheckStatus.FAIL, "No Objective section found")

        text = extract_text(obj_section).strip()
        if not text:
            return CheckResult("ST1", CheckStatus.FAIL, "Objective section is empty")
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
        if len(sentences) > 3:
            return CheckResult("ST1", CheckStatus.WARN, "Objective too long (>3 sentences)")
        return CheckResult("ST1", CheckStatus.PASS, "Objective OK")

    def _check_st2_scope_files(self, adf: dict) -> CheckResult:
        """ST2: Scope & Files — tables with real file paths."""
        scope_section = get_section_content(adf, "scope")
        if not scope_section:
            return CheckResult("ST2", CheckStatus.FAIL, "No Scope section found")

        tables = find_adf_nodes(scope_section, lambda n: n.get("type") == "table")
        if not tables:
            return CheckResult("ST2", CheckStatus.WARN, "Scope has no file tables")

        # Check for real file paths (not generic placeholders)
        text = extract_text(scope_section)
        paths = FILE_PATH_RE.findall(text)
        generic_markers = ["feature/", "component/", "module/", "xxx", "placeholder"]
        generic_count = sum(1 for p in paths if any(g in p.lower() for g in generic_markers))

        if not paths:
            return CheckResult("ST2", CheckStatus.WARN, "No file paths in scope tables")
        if generic_count > len(paths) / 2:
            return CheckResult(
                "ST2",
                CheckStatus.WARN,
                f"{generic_count}/{len(paths)} paths look generic",
            )
        return CheckResult("ST2", CheckStatus.PASS, f"{len(paths)} file paths OK")

    def _check_st3_acceptance_criteria(self, adf: dict) -> CheckResult:
        """ST3: AC format — Given/When/Then in panels."""
        ac_section = get_section_content(adf, "acceptance criteria")
        panels = [n for n in ac_section if n.get("type") == "panel"]

        if not panels:
            return CheckResult("ST3", CheckStatus.FAIL, "No AC panels found")

        gwt_count = 0
        for panel in panels:
            text = extract_text(panel)
            if GIVEN_RE.search(text) and WHEN_RE.search(text) and THEN_RE.search(text):
                gwt_count += 1

        if gwt_count == 0:
            return CheckResult("ST3", CheckStatus.FAIL, "No ACs have Given/When/Then")
        if gwt_count < len(panels):
            return CheckResult(
                "ST3",
                CheckStatus.WARN,
                f"{gwt_count}/{len(panels)} ACs have Given/When/Then",
            )
        return CheckResult("ST3", CheckStatus.PASS, f"{len(panels)} ACs correct")

    def _check_st4_tag_summary(self, adf: dict, wrapper: dict | None) -> CheckResult:
        """ST4: Tag & Summary — summary starts with [BE], [FE-Admin], [FE-Web], or [QA]."""
        if not wrapper:
            return CheckResult("ST4", CheckStatus.WARN, "No wrapper — cannot check summary")

        fmt, _ = detect_format(wrapper)
        summary = wrapper.get("summary", "")
        if not summary:
            if fmt == "edit":
                return CheckResult("ST4", CheckStatus.PASS, "EDIT format — summary set at creation")
            return CheckResult("ST4", CheckStatus.FAIL, "No summary field")

        if any(summary.startswith(tag) for tag in SUBTASK_TAGS):
            return CheckResult("ST4", CheckStatus.PASS, f"Summary tag OK: {summary[:20]}")

        return CheckResult(
            "ST4",
            CheckStatus.FAIL,
            f"Summary missing tag — must start with {'/'.join(SUBTASK_TAGS)}",
            fix_hint="Prepend [BE], [FE-Admin], [FE-Web], or [QA] to summary",
        )

    def _check_st5_language(self, adf: dict) -> CheckResult:
        """ST5: Language — Thai + English technical terms."""
        return self._check_language("ST5", adf)

    # ───────────────────────────────────────────────────────
    # Epic Quality Checks (E1–E4)
    # ───────────────────────────────────────────────────────

    def _check_e1_vision(self, adf: dict) -> CheckResult:
        """E1: Vision — Epic Overview section with clear problem statement."""
        overview = get_section_content(adf, "epic overview")
        if not overview:
            overview = get_section_content(adf, "overview")
        if not overview:
            return CheckResult("E1", CheckStatus.FAIL, "No Epic Overview section found")

        text = extract_text(overview).strip()
        if len(text.split()) < 5:
            return CheckResult("E1", CheckStatus.WARN, "Epic Overview too brief")
        return CheckResult("E1", CheckStatus.PASS, "Epic Overview present")

    def _check_e2_rice(self, adf: dict) -> CheckResult:
        """E2: RICE Score — table with Reach/Impact/Confidence/Effort."""
        rice_section = get_section_content(adf, "rice")
        if not rice_section:
            # RICE is optional per template (⚡ skip if priority is clear)
            return CheckResult("E2", CheckStatus.PASS, "RICE section skipped (optional)")

        tables = find_adf_nodes(rice_section, lambda n: n.get("type") == "table")
        if not tables:
            return CheckResult("E2", CheckStatus.WARN, "RICE section has no table")

        text = extract_text(rice_section).lower()
        factors = ["reach", "impact", "confidence", "effort"]
        found = [f for f in factors if f in text]
        if len(found) < 4:
            missing = [f for f in factors if f not in text]
            return CheckResult("E2", CheckStatus.WARN, f"RICE missing factors: {missing}")
        return CheckResult("E2", CheckStatus.PASS, "RICE score complete")

    def _check_e3_scope(self, adf: dict) -> CheckResult:
        """E3: Scope — features listed with must-have/should-have."""
        scope_section = get_section_content(adf, "scope")
        if not scope_section:
            return CheckResult("E3", CheckStatus.FAIL, "No Scope section found")

        text = extract_text(scope_section)
        if len(text.split()) < 10:
            return CheckResult("E3", CheckStatus.WARN, "Scope section too brief")
        return CheckResult("E3", CheckStatus.PASS, "Scope section present")

    def _check_e4_stories(self, adf: dict) -> CheckResult:
        """E4: User Stories — draft stories identified."""
        stories_section = get_section_content(adf, "user stories")
        if not stories_section:
            stories_section = get_section_content(adf, "stories")
        if not stories_section:
            return CheckResult("E4", CheckStatus.WARN, "No User Stories section found")

        panels = find_adf_nodes(stories_section, lambda n: n.get("type") == "panel")
        if not panels:
            text = extract_text(stories_section)
            if len(text.split()) < 5:
                return CheckResult("E4", CheckStatus.WARN, "User Stories section too brief")
        return CheckResult("E4", CheckStatus.PASS, "User Stories section present")

    # ───────────────────────────────────────────────────────
    # QA Quality Checks (QA1–QA5)
    # ───────────────────────────────────────────────────────

    def _check_qa1_coverage(self, adf: dict) -> CheckResult:
        """QA1: Coverage — AC Coverage table exists."""
        coverage = get_section_content(adf, "ac coverage")
        if not coverage:
            coverage = get_section_content(adf, "coverage")
        if not coverage:
            return CheckResult("QA1", CheckStatus.FAIL, "No AC Coverage section found")

        tables = find_adf_nodes(coverage, lambda n: n.get("type") == "table")
        if not tables:
            return CheckResult("QA1", CheckStatus.WARN, "AC Coverage has no table")
        return CheckResult("QA1", CheckStatus.PASS, "AC Coverage table present")

    def _check_qa2_test_format(self, adf: dict) -> CheckResult:
        """QA2: Test format — test cases have Given/When/Then."""
        tc_section = get_section_content(adf, "test cases")
        if not tc_section:
            tc_section = get_section_content(adf, "test")
        panels = find_adf_nodes(tc_section, lambda n: n.get("type") == "panel") if tc_section else []

        if not panels:
            return CheckResult("QA2", CheckStatus.FAIL, "No test case panels found")

        gwt_count = 0
        for panel in panels:
            text = extract_text(panel)
            if GIVEN_RE.search(text) and WHEN_RE.search(text) and THEN_RE.search(text):
                gwt_count += 1

        if gwt_count == 0:
            return CheckResult("QA2", CheckStatus.FAIL, "No TCs have Given/When/Then")
        if gwt_count < len(panels):
            return CheckResult(
                "QA2",
                CheckStatus.WARN,
                f"{gwt_count}/{len(panels)} TCs have Given/When/Then",
            )
        return CheckResult("QA2", CheckStatus.PASS, f"{len(panels)} TCs formatted correctly")

    def _check_qa3_scenarios(self, adf: dict) -> CheckResult:
        """QA3: Scenarios — grouped by type with correct panel colors."""
        tc_section = get_section_content(adf, "test cases")
        panels = find_adf_nodes(tc_section, lambda n: n.get("type") == "panel") if tc_section else []

        if not panels:
            return CheckResult("QA3", CheckStatus.FAIL, "No test scenario panels")

        types_found = set()
        for panel in panels:
            pt = panel.get("attrs", {}).get("panelType", "")
            types_found.add(pt)

        # Good QA should have at least happy path (success) and one of warning/error
        if "success" not in types_found:
            return CheckResult("QA3", CheckStatus.WARN, "No happy path tests (success panels)")
        if len(types_found) < 2:
            return CheckResult(
                "QA3",
                CheckStatus.WARN,
                "Only happy path — add edge case (warning) or error handling (error) tests",
            )
        return CheckResult("QA3", CheckStatus.PASS, f"Test types: {types_found}")

    def _check_qa4_test_data(self, adf: dict) -> CheckResult:
        """QA4: Test data — preconditions and data requirements mentioned."""
        full_text = extract_text(adf).lower()

        indicators = ["precondition", "test data", "prerequisite", "environment", "setup"]
        found = [i for i in indicators if i in full_text]

        if not found:
            return CheckResult(
                "QA4",
                CheckStatus.WARN,
                "No test data/precondition references found",
            )
        return CheckResult("QA4", CheckStatus.PASS, f"Test data indicators: {found}")

    def _check_qa5_language(self, adf: dict) -> CheckResult:
        """QA5: Language — Thai + English technical terms."""
        return self._check_language("QA5", adf)

    # ───────────────────────────────────────────────────────
    # Task Quality Checks (TK1–TK4)
    # ───────────────────────────────────────────────────────

    def _check_tk1_context(self, adf: dict) -> CheckResult:
        """TK1: Context — problem/reason section explaining why this task exists."""
        context_section = get_section_content(adf, "context")
        if not context_section:
            context_section = get_section_content(adf, "objective")
        if not context_section:
            context_section = get_section_content(adf, "bug description")
        if not context_section:
            return CheckResult("TK1", CheckStatus.FAIL, "No Context/Objective section found")

        text = extract_text(context_section).strip()
        if len(text.split()) < 5:
            return CheckResult("TK1", CheckStatus.WARN, "Context section too brief")
        return CheckResult("TK1", CheckStatus.PASS, "Context section present")

    def _check_tk2_actionable(self, adf: dict) -> CheckResult:
        """TK2: Actionable — has concrete tasks/phases/steps (panels or lists)."""
        full_text = extract_text(adf).lower()
        panels = find_adf_nodes(adf, lambda n: n.get("type") == "panel")
        lists = find_adf_nodes(adf, lambda n: n.get("type") in ("bulletList", "orderedList"))

        if len(panels) < 2 and len(lists) < 1:
            return CheckResult(
                "TK2",
                CheckStatus.FAIL,
                "No actionable items — need panels or lists with concrete steps",
            )
        # Check for action words
        action_words = [
            "install",
            "create",
            "update",
            "replace",
            "migrate",
            "remove",
            "delete",
            "add",
            "configure",
            "fix",
            "สร้าง",
            "ลบ",
            "เพิ่ม",
            "แก้",
        ]
        found = [w for w in action_words if w in full_text]
        if not found:
            return CheckResult("TK2", CheckStatus.WARN, "No action verbs found in content")
        return CheckResult("TK2", CheckStatus.PASS, f"Actionable content ({len(panels)} panels, {len(lists)} lists)")

    def _check_tk3_acceptance(self, adf: dict) -> CheckResult:
        """TK3: Acceptance criteria — table or list of done criteria."""
        ac_section = get_section_content(adf, "acceptance criteria")
        if not ac_section:
            ac_section = get_section_content(adf, "done criteria")
        if not ac_section:
            ac_section = get_section_content(adf, "fix criteria")

        if not ac_section:
            return CheckResult("TK3", CheckStatus.WARN, "No Acceptance Criteria section found")

        tables = find_adf_nodes(ac_section, lambda n: n.get("type") == "table")
        lists = find_adf_nodes(ac_section, lambda n: n.get("type") in ("bulletList", "orderedList"))

        if tables or lists:
            return CheckResult("TK3", CheckStatus.PASS, "Acceptance criteria present")
        return CheckResult("TK3", CheckStatus.WARN, "AC section has no table or list")

    def _check_tk4_language(self, adf: dict) -> CheckResult:
        """TK4: Language — Thai + English technical terms."""
        return self._check_language("TK4", adf)

    # ───────────────────────────────────────────────────────
    # Shared Helpers
    # ───────────────────────────────────────────────────────

    def _check_language(self, check_id: str, adf: dict) -> CheckResult:
        """Shared language check — Thai content with English technical terms."""
        plain_texts: list[str] = []

        def _collect(n: dict) -> None:
            if n.get("type") == "text" and "text" in n and not has_code_mark(n):
                plain_texts.append(n["text"])

        walk_adf(adf, _collect)
        text = " ".join(plain_texts)

        if not text:
            return CheckResult(check_id, CheckStatus.WARN, "No text content found")
        if THAI_RE.search(text):
            return CheckResult(check_id, CheckStatus.PASS, "Thai language detected")
        return CheckResult(
            check_id,
            CheckStatus.FAIL,
            "No Thai text — content should be in Thai",
        )

    # ───────────────────────────────────────────────────────
    # Auto-Fix Methods
    # ───────────────────────────────────────────────────────

    def _fix_panel_types(self, adf: dict) -> int:
        """Fix invalid panel types → 'info'."""
        fixed = 0

        def _fix(n: dict) -> None:
            nonlocal fixed
            if n.get("type") == "panel":
                pt = n.get("attrs", {}).get("panelType")
                if pt not in VALID_PANEL_TYPES:
                    n.setdefault("attrs", {})["panelType"] = "info"
                    fixed += 1

        walk_adf(adf, _fix)
        return fixed

    def _fix_code_marks(self, adf: dict) -> int:
        """Add code marks to text nodes containing file paths or API routes."""
        fixed = 0

        def _fix(n: dict) -> None:
            nonlocal fixed
            if n.get("type") != "text" or "text" not in n:
                return
            if has_code_mark(n) or has_link_mark(n):
                return
            text = n["text"]
            if FILE_PATH_RE.search(text) or API_ROUTE_RE.search(text):
                marks = n.get("marks", [])
                marks.append({"type": "code"})
                n["marks"] = marks
                fixed += 1

        walk_adf(adf, _fix)
        return fixed
