"""ADF Validator — Quality Gate enforcement for Jira ADF documents.

Validates ADF JSON against templates.md + verification-checklist.md rules.
Supports: Story, Subtask, Epic, QA, Task issue types.
Scoring: pass=1, warn=0.5, fail=0. Overall >=90% = pass.

Usage (via scripts/validate_adf.py):
    python validate_adf.py tasks/story.json --type story
    python validate_adf.py tasks/story.json --type story --fix
    python validate_adf.py tasks/story.json --type story --dual-zone-strict
    python validate_adf.py tasks/story.json --type story --markdown-strict

Checks by issue type (v3.16.1):
    Story:   T1-T5 + S1-S7, S8                                         = 13 checks
    Subtask: T1-T5 + ST1-ST5                                           = 10 checks
    Epic:    T1-T10, T12, T13, T14 + E1-E4 + S7, S8                   = 19 checks
    QA:      T1-T5 + QA1-QA5                                           = 10 checks
    Task:    T1-T8, T10-T16 + TK1-TK4 + S7, S8                        = 21 checks

S7: Markdown-in-text scan — detects raw markdown syntax inside ADF text nodes.
    Severity: WARN by default (grandfather mode, v3.16.1 hotfix).
    Set markdown_strict=True (or --markdown-strict) to get FAIL/ERROR behaviour.
    Default flips to FAIL in v3.17.0.
S8: Dual-zone AC check (ERROR for missing required zone; WARN for language leaks) —
    verifies Business + Developer H3 zones present per per-type matrix.
    Default mode: grandfather (warn-only). Strict mode: --dual-zone-strict.
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

# T6: Ambiguity cue words — trigger Scope Disambiguation guidance when 2+ appear in title,
# or 1+ appears in description without explicit "Scope:" / "Trigger:" clarification.
# See references/templates-epic.md + references/architect-debate-protocol.md.
AMBIGUOUS_CUE_WORDS = frozenset({
    "request",
    "process",
    "handle",
    "manage",
    "review",
    "check",
    "trigger",
    "send",
    "notify",
    "update",
})

# T7: Canonical Scope Disambiguation heading regex (v3.12.1 — G1).
# Allows `Scope Disambiguation`, `Scope Disambiguation — TH subtitle`, `Scope Disambiguation: ...`.
# Reject near-miss variants like `Scope Clarification` / `Disambiguation Notes` so agents
# converge on one canonical heading (QA can grep for it across epics).
CANONICAL_DISAMBIG_RE = re.compile(r"^scope\s+disambiguation(?:\s*[—:\-].*)?$", re.IGNORECASE)

# T9: Jira issue key pattern inside inlineCard URLs (v3.12.1 — G6 bilateral ref rule).
JIRA_KEY_IN_URL_RE = re.compile(r"/browse/([A-Z][A-Z0-9]+-\d+)")

# T10: Jira key in plain text — detects `TP-XXX` appearing as text not wrapped in inlineCard.
JIRA_KEY_IN_TEXT_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")

# T11: Vertical slice markers in Task title — `Slice A`, `vs1-`, `vs-enabler-`.
SLICE_MARKER_RE = re.compile(r"(?:\bSlice\s+[A-Z]\b|\bvs\d+-|\bvs-enabler-)", re.IGNORECASE)

# T13: Bare method-call pattern: `handle()`, `run()`, `process()` — no class prefix.
# Matches inline code text that is a lowercase-initial word followed by `()` with nothing else.
BARE_METHOD_RE = re.compile(r"^[a-z][a-zA-Z0-9_]*\(\)$")

# T16: Flag discipline for ship-per-merge slices (v3.13.0).
# Slice tickets (vs-*) should reference `.flags.yaml` entry via flag name OR
# include an explicit "no flag (hardening)" note. Flag naming convention: `feat/{epic-key}/s{N}`.
FLAG_NAME_RE = re.compile(r"\bfeat/[A-Z][A-Z0-9]+-\d+/s\d+\b")
HARDENING_NOTE_RE = re.compile(
    r"no\s+flag\s*\(\s*hardening\s*\)|hardening\s+slice\s*[—:-]\s*no\s+flag|ไม่ใช้\s*flag\s*\(\s*hardening\s*\)",
    re.IGNORECASE,
)

# S7: Markdown-in-text patterns — ADF text nodes must NOT contain raw markdown syntax.
# These patterns signal the agent emitted markdown prose instead of ADF structural blocks.
MARKDOWN_IN_TEXT_PARA_BREAK_RE = re.compile(r"\n\n")
MARKDOWN_IN_TEXT_TABLE_ROW_RE = re.compile(r"^\|.+\|", re.MULTILINE)
MARKDOWN_IN_TEXT_BULLET_RE = re.compile(r"^[•\-\*] ", re.MULTILINE)
MARKDOWN_IN_TEXT_HEADING_RE = re.compile(r"^#{1,6} ", re.MULTILINE)

# S8: Dual-zone AC heading patterns.
# Business zone heading contains "business" or "มุมธุรกิจ" (case-insensitive).
# Developer zone heading contains "developer" or "มุม dev" or "dev/qa" (case-insensitive).
S8_BUSINESS_ZONE_RE = re.compile(r"business|มุมธุรกิจ", re.IGNORECASE)
S8_DEVELOPER_ZONE_RE = re.compile(r"developer|มุม\s*dev|dev/qa", re.IGNORECASE)

# S8: Banned jargon tokens in Business AC zone.
S8_BANNED_SLA_RE = re.compile(r"\b\d+\s*(?:ms|s|sec|seconds|minutes)\b", re.IGNORECASE)
S8_BANNED_SERVICE_RE = re.compile(
    r"\b(?:Pusher|Redis|Kafka|S3|SQS|SNS|RabbitMQ|Postgres|MySQL|MongoDB)\b",
    re.IGNORECASE,
)
S8_BANNED_PATTERN_RE = re.compile(
    r"\b(?:async|sync|fire-and-forget|debounce|throttle|dedupe|idempotent|retry|backoff|circuit-breaker)\b",
    re.IGNORECASE,
)
S8_BANNED_METHOD_RE = re.compile(r"\w+\.\w+\(")
S8_BANNED_FIELD_RE = re.compile(r"customfield_\d+")

# S8: Per-type requirement matrix.
# Values: "required", "optional", "skip".
S8_BUSINESS_ZONE_REQUIRED: dict[str, str] = {
    "epic": "required",
    "story": "required",
    "task": "optional",  # required if user-facing — enforced by language-leak check
    "subtask": "skip",
    "bug": "required",
    "qa": "optional",
}
S8_DEVELOPER_ZONE_REQUIRED: dict[str, str] = {
    "epic": "required",
    "story": "required",
    "task": "required",
    "subtask": "required",
    "bug": "required",
    "qa": "optional",
}

# T14: Vague AC phrase dictionary (G11 INVEST-T).
VAGUE_AC_PHRASES: tuple[str, ...] = (
    "should work",
    "works correctly",
    "works properly",
    "ทำงานได้ดี",
    "ทำงานถูกต้อง",
    "ทำงานเหมาะสม",
    "handle properly",
    "handles correctly",
    "จัดการได้",
    "จัดการถูกต้อง",
    "user-friendly",
    "ใช้งานง่าย",
    "perform well",
    "ทำงานเร็ว",
    "as expected",
    "ตามที่คาดหวัง",
)

# G3: Decision-path verbs that need an explicit qualifier (auto- / manual- / admin-)
# when they appear in slice/task titles. Documented in templates-task.md + templates-epic.md.
DECISION_PATH_VERBS = frozenset({
    "approve",
    "reject",
    "decide",
    "process",
    # Thai equivalents used in slice titles
    "อนุมัติ",
    "ปฏิเสธ",
    "ตัดสิน",
})
DECISION_PATH_QUALIFIERS_RE = re.compile(r"\b(auto|manual|admin)-", re.IGNORECASE)

_ALL_SECTION_KEYS: frozenset[str] = frozenset({
    "acceptance criteria",
    "user story",
    "narrative",
    "scope",
    "objective",
    "epic overview",
    "overview",
    "rice",
    "user stories",
    "stories",
    "ac coverage",
    "coverage",
    "test cases",
    "test",
    "context",
    "bug description",
    "done criteria",
    "fix criteria",
    "reference",
})

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
    threshold: float = QG_THRESHOLD

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
        return self.score >= self.threshold

    def to_dict(self) -> dict[str, Any]:
        counts = {"pass": 0, "warn": 0, "fail": 0}
        for c in self.checks:
            counts[c.status.value] += 1
        return {
            "issue_type": self.issue_type,
            "score": round(self.score, 1),
            "threshold": self.threshold,
            "status": "pass" if self.score >= self.threshold else "warn" if self.score >= 70 else "fail",
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
        Story:   T1-T5 (technical) + S1-S8 (quality)                     = 13 checks
        Subtask: T1-T5 (technical) + ST1-ST5 (quality)                   = 10 checks
        Epic:    T1-T10, T12, T13, T14 (T6-T14 WARN-only) + E1-E4 + S7, S8 = 19 checks
        QA:      T1-T5 (technical) + QA1-QA5 (quality)                   = 10 checks
        Task:    T1-T8, T10-T16 (T6-T16 WARN-only) + TK1-TK4 + S7, S8    = 21 checks

    T6-T16 are WARN-only so they cannot break existing tickets — scoring still permits
    PASS at 90% threshold.

    v3.12.1 (G1/G2/G6): T7 canonical Scope Disambiguation heading, T8 decision-path
    qualifier, T9 bilateral Epic reference rule added for Epic/Task types.

    v3.12.2 (G7-G12): T10 explicit Jira dependency links (inlineCard for TP-keys),
    T11 Estimate section (Task-only), T12 paired-epic regression AC (Task-only),
    T13 code reference format (bare method check), T14 vague AC phrase scan,
    T15 Out of Scope required for vertical slices (Task-only).

    v3.16.0: S7 markdown-in-text scan (ERROR — raw markdown syntax inside text nodes),
    S8 dual-zone AC check (ERROR for missing required zone, WARN for language leaks).
    S8 defaults to grandfather/warn-only mode; pass dual_zone_strict=True for ERROR.

    v3.16.1 hotfix: S7 demoted to WARN by default so existing tickets with legacy text
    blobs are not suddenly broken after users pull the update. Pass markdown_strict=True
    (or --markdown-strict CLI flag) to restore ERROR behaviour. Default flips back to
    FAIL in v3.17.0.

    Args:
        threshold: QG pass threshold (0-100). Defaults to QG_THRESHOLD (90.0).
        dual_zone_strict: When True, S8 emits FAIL for missing zones instead of WARN.
            Defaults to False (grandfather mode). Flip to True in v3.17.0.
        markdown_strict: When True, S7 emits FAIL for markdown-in-text violations
            instead of WARN. Defaults to False (grandfather mode). Flip to True in
            v3.17.0.
    """

    def __init__(
        self,
        threshold: float = QG_THRESHOLD,
        dual_zone_strict: bool = False,
        markdown_strict: bool = False,
    ) -> None:
        self.threshold = threshold
        self.dual_zone_strict = dual_zone_strict
        self.markdown_strict = markdown_strict

    def _extract_sections(self, adf: dict) -> dict[str, list[dict]]:
        """Pre-extract all known sections in one pass. Returns {heading_pattern: content_nodes}."""
        return {key: get_section_content(adf, key) for key in _ALL_SECTION_KEYS}

    def validate(
        self,
        adf: dict,
        issue_type: str,
        wrapper: dict | None = None,
    ) -> ValidationReport:
        """Run all applicable checks for the issue type."""
        report = ValidationReport(issue_type=issue_type, threshold=self.threshold)
        _secs = self._extract_sections(adf)

        # Technical checks (all types)
        report.checks.append(self._check_t1_adf_format(adf))
        report.checks.append(self._check_t2_panels(adf))
        report.checks.append(self._check_t3_inline_code(adf))
        report.checks.append(self._check_t4_links(adf, issue_type, _secs))
        report.checks.append(self._check_t5_required_fields(adf, issue_type, wrapper))

        # T6-T9 only apply to Epic + Task (the types most affected by title-scope ambiguity).
        # Stories/subtasks inherit context from parents so their titles are usually unambiguous.
        if issue_type in ("epic", "task"):
            report.checks.append(self._check_t6_ambiguity(adf, wrapper))
            report.checks.append(self._check_t7_canonical_disambig(adf, wrapper))
            report.checks.append(self._check_t8_decision_path_qualifier(wrapper))
        if issue_type == "epic":
            report.checks.append(self._check_t9_bilateral_epic_ref(adf))

        # v3.12.2 (G7-G12): T10-T15 WARN-only checks.
        # T10 (explicit Jira links), T12 (paired-epic regression), T13 (code reference format),
        # T14 (vague AC phrases) — Epic + Task. T11 (Estimate) + T15 (Out of Scope) — Task only.
        if issue_type in ("epic", "task"):
            report.checks.append(self._check_t10_explicit_jira_links(adf))
            report.checks.append(self._check_t12_paired_epic_regression(adf, _secs))
            report.checks.append(self._check_t13_code_reference_format(adf))
            report.checks.append(self._check_t14_vague_ac_phrases(adf, _secs))
        if issue_type == "task":
            report.checks.append(self._check_t11_estimate(adf, _secs))
            report.checks.append(self._check_t15_out_of_scope_for_slice(adf, wrapper))
            report.checks.append(self._check_t16_flag_discipline(adf, wrapper))

        # S7 + S8: markdown-in-text and dual-zone AC — apply to Story, Epic, Task.
        if issue_type in ("story", "epic", "task"):
            report.checks.append(self._check_s7_markdown_in_text(adf))
            report.checks.append(self._check_s8_dual_zone_ac(adf, issue_type))

        # Type-specific quality checks
        quality_map: dict[str, list[Callable]] = {
            "story": [
                lambda: self._check_s1_invest(_secs),
                lambda: self._check_s2_narrative(_secs, adf),
                lambda: self._check_s3_anti_patterns(_secs),
                lambda: self._check_s4_acceptance_criteria(_secs),
                lambda: self._check_s5_scope(adf, _secs),
                lambda: self._check_s6_language(adf),
            ],
            "subtask": [
                lambda: self._check_st1_objective(_secs),
                lambda: self._check_st2_scope_files(_secs),
                lambda: self._check_st3_acceptance_criteria(_secs),
                lambda: self._check_st4_tag_summary(adf, wrapper),
                lambda: self._check_st5_language(adf),
            ],
            "epic": [
                lambda: self._check_e1_vision(_secs),
                lambda: self._check_e2_rice(_secs),
                lambda: self._check_e3_scope(_secs),
                lambda: self._check_e4_stories(_secs),
            ],
            "qa": [
                lambda: self._check_qa1_coverage(_secs),
                lambda: self._check_qa2_test_format(_secs),
                lambda: self._check_qa3_scenarios(_secs),
                lambda: self._check_qa4_test_data(adf),
                lambda: self._check_qa5_language(adf),
            ],
            "task": [
                lambda: self._check_tk1_context(_secs),
                lambda: self._check_tk2_actionable(adf),
                lambda: self._check_tk3_acceptance(_secs),
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

    def _check_t4_links(self, adf: dict, issue_type: str, _secs: dict) -> CheckResult:
        """T4: Links — reference section exists with links."""
        # Find link marks or inlineCard nodes
        links = find_adf_nodes(
            adf,
            lambda n: n.get("type") == "inlineCard" or (n.get("type") == "text" and has_link_mark(n)),
        )
        ref_section = _secs.get("reference", [])

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
        del issue_type
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

    def _check_t6_ambiguity(self, adf: dict, wrapper: dict | None) -> CheckResult:
        """T6: Title Ambiguity Scan (WARN-level, never FAIL).

        Scans Epic/Task summary + description text for ambiguous cue words. Triggers when:
          - Title contains 2+ cue words without a Scope Disambiguation section, OR
          - Description contains a cue word without explicit 'Scope:' or 'Trigger:' clarification.

        See references/templates-epic.md 'Scope Disambiguation' section and
        references/architect-debate-protocol.md for the resolution workflow.
        """
        # Extract title from wrapper if available
        title = ""
        if wrapper:
            title = wrapper.get("summary", "") or ""

        title_lower = title.lower()
        title_cues = sorted({w for w in AMBIGUOUS_CUE_WORDS if re.search(rf"\b{re.escape(w)}\b", title_lower)})

        # Scan for the Scope Disambiguation heading anywhere in the document
        has_disambig_section = bool(find_adf_nodes(
            adf,
            lambda n: n.get("type") == "heading"
            and "scope disambiguation" in extract_text(n).lower(),
        ))

        # Full description plain text (excluding code marks so we don't flag file paths)
        desc_texts: list[str] = []

        def _collect(n: dict) -> None:
            if n.get("type") == "text" and "text" in n and not has_code_mark(n):
                desc_texts.append(n["text"])

        walk_adf(adf, _collect)
        desc_text = " ".join(desc_texts).lower()
        desc_has_clarifier = ("scope:" in desc_text) or ("trigger:" in desc_text)
        desc_cues = sorted({w for w in AMBIGUOUS_CUE_WORDS if re.search(rf"\b{re.escape(w)}\b", desc_text)})

        # Rule 1: Title has 2+ cue words but no Scope Disambiguation section
        if len(title_cues) >= 2 and not has_disambig_section:
            return CheckResult(
                "T6",
                CheckStatus.WARN,
                f"Title contains ambiguous cue words: {title_cues}. "
                "Consider adding Scope Disambiguation section to clarify "
                "(see templates-epic.md).",
                fix_hint="Add H2 'Scope Disambiguation' after สรุปภาพรวม with explicit interpretation.",
            )

        # Rule 2: Description has cue words but no explicit Scope/Trigger clarifier and no section
        if desc_cues and not desc_has_clarifier and not has_disambig_section and len(desc_text.split()) > 50:
                return CheckResult(
                    "T6",
                    CheckStatus.WARN,
                    f"Description contains ambiguous cue words: {desc_cues} "
                    "without explicit 'Scope:' or 'Trigger:' clarification. "
                    "Consider adding Scope Disambiguation section (see templates-epic.md).",
                    fix_hint="Add Scope Disambiguation section OR inline 'Scope:' / 'Trigger:' lines.",
                )

        return CheckResult("T6", CheckStatus.PASS, "No title/description ambiguity detected")

    def _check_t7_canonical_disambig(self, adf: dict, wrapper: dict | None) -> CheckResult:
        """T7: Canonical Scope Disambiguation heading (WARN-level, v3.12.1 — G1).

        When title has ambiguous cue words, T6 warns that *some* disambiguation is missing.
        T7 goes further: the section MUST use the canonical heading `Scope Disambiguation`
        (allowing TH subtitle separator `—` / `:`), not near-miss variants like
        `Scope Clarification` or `Disambiguation Notes`. A canonical heading lets QA grep
        across all epics and ensures readers converge on one known anchor.
        """
        title = (wrapper or {}).get("summary", "") or ""
        title_lower = title.lower()
        title_cues = sorted({w for w in AMBIGUOUS_CUE_WORDS if re.search(rf"\b{re.escape(w)}\b", title_lower)})

        if len(title_cues) < 2:
            # T7 only fires when T6 would also have fired on the title — otherwise N/A.
            return CheckResult("T7", CheckStatus.PASS, "T7 N/A (title has <2 cue words)")

        headings = find_headings(adf, level=2)
        canonical = False
        near_miss: list[str] = []
        for h in headings:
            heading_text = extract_text(h).strip()
            if CANONICAL_DISAMBIG_RE.match(heading_text):
                canonical = True
                break
            low = heading_text.lower()
            if ("disambiguation" in low or "scope clarif" in low) and not canonical:
                near_miss.append(heading_text)

        if canonical:
            return CheckResult("T7", CheckStatus.PASS, "Canonical 'Scope Disambiguation' heading found")
        if near_miss:
            return CheckResult(
                "T7",
                CheckStatus.WARN,
                f"Near-miss heading '{near_miss[0]}' — use canonical 'Scope Disambiguation' "
                "(allows TH subtitle separator '—' or ':').",
                fix_hint="Rename H2 heading to exactly 'Scope Disambiguation'.",
            )
        return CheckResult(
            "T7",
            CheckStatus.WARN,
            f"Title cue words {title_cues} require canonical 'Scope Disambiguation' H2 heading; none found.",
            fix_hint="Add H2 'Scope Disambiguation' section after สรุปภาพรวม (see templates-epic.md).",
        )

    def _check_t8_decision_path_qualifier(self, wrapper: dict | None) -> CheckResult:
        """T8: Decision-path qualifier (WARN-level, v3.12.1 — G3).

        Tasks/slices that describe AI or system decision paths (approve, reject, decide,
        process, Thai: อนุมัติ/ปฏิเสธ/ตัดสิน) should include an explicit qualifier:
        `auto-` / `manual-` / `admin-`. An unqualified verb is ambiguous — could be auto
        decision or manual admin action. See templates-task.md `Decision-Path Qualifier Rule`.
        """
        title = (wrapper or {}).get("summary", "") or ""
        if not title:
            return CheckResult("T8", CheckStatus.PASS, "T8 N/A (no title)")

        title_lower = title.lower()
        matched_verbs: list[str] = []
        for v in DECISION_PATH_VERBS:
            is_english = bool(re.fullmatch(r"[A-Za-z]+", v))
            if is_english:
                if re.search(rf"\b{re.escape(v)}\b", title_lower):
                    matched_verbs.append(v)
            else:
                # Thai: no word boundary (Thai lacks ASCII word boundaries)
                if v in title:
                    matched_verbs.append(v)
        matched_verbs = sorted(set(matched_verbs))

        if not matched_verbs:
            return CheckResult("T8", CheckStatus.PASS, "No decision-path verb in title")

        if DECISION_PATH_QUALIFIERS_RE.search(title):
            return CheckResult("T8", CheckStatus.PASS, f"Decision-path verb {matched_verbs} has qualifier")

        return CheckResult(
            "T8",
            CheckStatus.WARN,
            f"Title contains decision-path verb {matched_verbs} without explicit qualifier "
            "(auto- / manual- / admin-). Ambiguous — is it automatic or human action?",
            fix_hint="Prefix the verb with 'auto-' (system-decided) or 'manual-'/'admin-' (human-decided). "
            "Example: 'AI auto-อนุมัติสื่อ' or 'Admin manual-อนุมัติสื่อ' (see templates-task.md).",
        )

    def _check_t9_bilateral_epic_ref(self, adf: dict) -> CheckResult:
        """T9: Bilateral Epic Reference (WARN-level, Epic-only, v3.12.1 — G6).

        When an Epic references another Epic via `inlineCard`, the Coverage Matrix must
        include a `Related Epic(s)` column with explicit keys (or `—`). Validator cannot
        fetch the sibling Epic to confirm the mirror reference, so it checks the local
        signal: if Epic description cites other TP-XXX keys via inlineCard AND has a
        Coverage Matrix, the matrix must include a `Related Epic` column entry.
        """
        inline_cards = find_adf_nodes(adf, lambda n: n.get("type") == "inlineCard")
        referenced_keys: list[str] = []
        for card in inline_cards:
            url = card.get("attrs", {}).get("url", "") or ""
            m = JIRA_KEY_IN_URL_RE.search(url)
            if m:
                referenced_keys.append(m.group(1))

        if not referenced_keys:
            return CheckResult("T9", CheckStatus.PASS, "T9 N/A (no inlineCard Epic references)")

        # Look for Coverage Matrix section (H3 in Technical Reference zone)
        headings = find_headings(adf)
        matrix_heading = None
        for h in headings:
            if "coverage matrix" in extract_text(h).lower():
                matrix_heading = h
                break

        if not matrix_heading:
            return CheckResult(
                "T9",
                CheckStatus.WARN,
                f"Epic references other keys {sorted(set(referenced_keys))} via inlineCard but "
                "no 'Coverage Matrix' section found. Bilateral references require a Coverage Matrix "
                "with 'Related Epic(s)' column (see templates-epic.md P3 rule).",
                fix_hint="Add H3 'Coverage Matrix' table with columns: Scenario | This Epic | Related Epic(s) | Out of Scope.",
            )

        # Check the doc text for 'Related Epic' column header phrase
        full_text = extract_text(adf).lower()
        if "related epic" not in full_text:
            return CheckResult(
                "T9",
                CheckStatus.WARN,
                "Coverage Matrix found but missing 'Related Epic(s)' column — bilateral reference "
                f"rule requires explicit keys for {sorted(set(referenced_keys))} (or `—`).",
                fix_hint="Add a 'Related Epic(s)' column to the Coverage Matrix with each referenced Epic key.",
            )

        return CheckResult("T9", CheckStatus.PASS, f"Bilateral refs documented for {sorted(set(referenced_keys))}")

    # ───────────────────────────────────────────────────────
    # v3.12.2 Proactive Prevention Checks (T10–T15, all WARN-only)
    # ───────────────────────────────────────────────────────

    def _check_t10_explicit_jira_links(self, adf: dict) -> CheckResult:
        """T10: Explicit Jira Dependency Links (WARN-level, v3.12.2 — G7).

        When `TP-XXX` appears in description text (not inside inlineCard), warn — the
        reference must use `inlineCard` so Jira renders a link preview + dependency
        graph picks it up. Plain text references slip past reviewers and aren't
        machine-checkable.

        Validator operates on ADF only; it cannot confirm the actual Jira issue
        link exists. This check only enforces the textual convention.
        """
        inline_cards = find_adf_nodes(adf, lambda n: n.get("type") == "inlineCard")
        carded_keys: set[str] = set()
        for card in inline_cards:
            url = card.get("attrs", {}).get("url", "") or ""
            m = JIRA_KEY_IN_URL_RE.search(url)
            if m:
                carded_keys.add(m.group(1))

        plain_keys: set[str] = set()

        def _scan_text(n: dict) -> None:
            if n.get("type") == "text" and "text" in n and not has_code_mark(n) and not has_link_mark(n):
                for match in JIRA_KEY_IN_TEXT_RE.finditer(n["text"]):
                    plain_keys.add(match.group(1))

        walk_adf(adf, _scan_text)

        unlinked = sorted(plain_keys - carded_keys)
        if not unlinked:
            return CheckResult("T10", CheckStatus.PASS, f"Jira key references properly linked ({len(carded_keys)} cards)")

        return CheckResult(
            "T10",
            CheckStatus.WARN,
            f"Plain-text Jira key(s) {unlinked} not rendered as inlineCard — "
            "dependency graph won't pick them up. Wrap each key in inlineCard AND "
            "set a Jira link type (Blocks / Is blocked by / Relates to / Depends on).",
            fix_hint="Replace {text: 'TP-XXX'} with inlineCard {url: '.../browse/TP-XXX'} "
            "and run `acli jira workitem link --key SRC --target DST --type 'Blocks'`.",
        )

    def _check_t11_estimate(self, adf: dict, _secs: dict) -> CheckResult:
        """T11: Estimate Declaration (WARN-level, Task-only, v3.12.2 — G8).

        Task description should declare an estimate (Story Points + days) in a
        dedicated section — not only via Jira field. Forces explicit size reasoning
        + prevents scope creep (>8 SP slices signal split-needed).
        """
        del _secs
        full_text_lower = extract_text(adf).lower()

        # Look for H2 heading with estimate-keyword, OR a table containing "story points" label.
        headings = find_headings(adf, level=2)
        heading_match = False
        for h in headings:
            h_text = extract_text(h).lower().strip()
            if "estimate" in h_text or "ประมาณการ" in h_text:
                heading_match = True
                break

        has_story_points = "story points" in full_text_lower or "story point" in full_text_lower

        if heading_match or has_story_points:
            return CheckResult("T11", CheckStatus.PASS, "Estimate declared in description")

        return CheckResult(
            "T11",
            CheckStatus.WARN,
            "No Estimate / ประมาณการ section in description — slice size not declared inline. "
            "Add H2 'ประมาณการ (Estimate)' with story points + days table.",
            fix_hint="Add section with `| Story Points | Days | Confidence |` table; "
            "slices with 8+ SP should be split (SPIDR).",
        )

    def _check_t12_paired_epic_regression(self, adf: dict, _secs: dict) -> CheckResult:
        """T12: Paired-Epic Regression ACs (WARN-level, v3.12.2 — G9).

        When description references another Epic/Task via inlineCard, AC section
        should mention that key at least once — a regression marker guarding the
        paired-epic scope. Prevents silent cross-boundary behavior.
        """
        inline_cards = find_adf_nodes(adf, lambda n: n.get("type") == "inlineCard")
        referenced_keys: set[str] = set()
        for card in inline_cards:
            url = card.get("attrs", {}).get("url", "") or ""
            m = JIRA_KEY_IN_URL_RE.search(url)
            if m:
                referenced_keys.add(m.group(1))

        # Also consider text-plain TP keys so we don't silently miss cases T10 flagged.
        def _scan_plain_keys(n: dict) -> None:
            if n.get("type") == "text" and "text" in n:
                for match in JIRA_KEY_IN_TEXT_RE.finditer(n["text"]):
                    referenced_keys.add(match.group(1))

        walk_adf(adf, _scan_plain_keys)

        if not referenced_keys:
            return CheckResult("T12", CheckStatus.PASS, "T12 N/A (no paired-epic keys referenced)")

        ac_section = (
            _secs.get("acceptance criteria") or _secs.get("done criteria") or _secs.get("fix criteria") or []
        )
        ac_text = extract_text(ac_section) if ac_section else ""

        referenced_in_ac = {k for k in referenced_keys if k in ac_text}
        if referenced_in_ac:
            return CheckResult(
                "T12",
                CheckStatus.PASS,
                f"Regression AC(s) reference paired key(s) {sorted(referenced_in_ac)}",
            )

        return CheckResult(
            "T12",
            CheckStatus.WARN,
            f"Description references paired key(s) {sorted(referenced_keys)} but AC section "
            "does not mention them — add a regression AC (❌ prefix) guarding the paired scope.",
            fix_hint="Add `❌ AC_N: regression — [paired-Epic scope] does NOT trigger this slice's behavior "
            "(Paired: TP-XXX)` to Acceptance Criteria.",
        )

    def _check_t13_code_reference_format(self, adf: dict) -> CheckResult:
        """T13: Code Reference Format (WARN-level, v3.12.2 — G10).

        Inline `code`-marked text that looks like a bare method call (`handle()`,
        `run()`, `process()`) without a class prefix is too ambiguous across
        sibling tickets. Warn and suggest class.method() or full path form.
        """
        bare_methods: list[str] = []

        def _scan(n: dict) -> None:
            if n.get("type") != "text" or "text" not in n:
                return
            if not has_code_mark(n):
                return
            text = n["text"].strip()
            if BARE_METHOD_RE.match(text):
                bare_methods.append(text)

        walk_adf(adf, _scan)

        if not bare_methods:
            return CheckResult("T13", CheckStatus.PASS, "Code references use class/path context")

        sample = sorted(set(bare_methods))[:3]
        return CheckResult(
            "T13",
            CheckStatus.WARN,
            f"Bare method reference(s) in inline code: {sample} — add class prefix "
            "(e.g. `AiMediaAnalysisJob.handle()`) or full path (`app/Jobs/Foo.ts:Foo.handle()`). "
            "Bare `handle()` is ambiguous across sibling tickets.",
            fix_hint="Change inline code `handle()` → `ClassName.handle()` or full path form "
            "(see templates-core.md Code Reference Format).",
        )

    def _check_t14_vague_ac_phrases(self, adf: dict, _secs: dict) -> CheckResult:
        """T14: Vague AC Phrase Scan (WARN-level, v3.12.2 — G11).

        Scans AC / `เงื่อนไขที่ต้องผ่าน` / done-criteria / fix-criteria sections
        for vague phrases that break INVEST-Testable. Warn with suggested rephrase.
        """
        del adf
        sections_to_scan: list[dict] = []
        for key in ("acceptance criteria", "done criteria", "fix criteria"):
            sections_to_scan.extend(_secs.get(key, []) or [])

        if not sections_to_scan:
            return CheckResult("T14", CheckStatus.PASS, "T14 N/A (no AC section to scan)")

        ac_text_lower = extract_text(sections_to_scan).lower()
        matched: list[str] = [phrase for phrase in VAGUE_AC_PHRASES if phrase.lower() in ac_text_lower]

        if not matched:
            return CheckResult("T14", CheckStatus.PASS, "AC phrasing testable (no vague phrases)")

        return CheckResult(
            "T14",
            CheckStatus.WARN,
            f"Vague phrase(s) in AC section: {matched[:3]} — not testable. "
            "Replace with Given/When/Then + specific values, time bounds, or observable UI state.",
            fix_hint="Example rewrite: 'System handles properly' → "
            "'Given X, When Y, Then Z (specific assertion with values)'.",
        )

    def _check_t15_out_of_scope_for_slice(self, adf: dict, wrapper: dict | None) -> CheckResult:
        """T15: Out of Scope REQUIRED for Vertical Slices (WARN-level, Task-only, v3.12.2 — G12).

        When Task title indicates it is a vertical slice (`Slice A/B/C`, `vs1-`,
        `vs-enabler-`) or labels include `vs*`, the description MUST have an
        `Out of Scope` / `ไม่รวมงานนี้` section to force explicit boundary decisions.
        """
        title = (wrapper or {}).get("summary", "") or ""
        labels = (wrapper or {}).get("labels", []) or []

        is_slice = bool(SLICE_MARKER_RE.search(title)) or any(
            str(label).lower().startswith("vs") for label in labels
        )

        if not is_slice:
            return CheckResult("T15", CheckStatus.PASS, "T15 N/A (not a vertical slice)")

        headings = find_headings(adf, level=2)
        has_oos_section = False
        for h in headings:
            h_text = extract_text(h).lower().strip()
            if "out of scope" in h_text or "ไม่รวมงานนี้" in h_text or "ไม่รวม" in h_text:
                has_oos_section = True
                break

        if has_oos_section:
            return CheckResult("T15", CheckStatus.PASS, "Out of Scope section present for slice")

        return CheckResult(
            "T15",
            CheckStatus.WARN,
            f"Slice title '{title[:40]}' missing 'Out of Scope' / 'ไม่รวมงานนี้' section. "
            "Vertical slices MUST list explicit boundary (sibling slice scope, paired-epic scope, "
            "deferred work).",
            fix_hint="Add H2 'ไม่รวมงานนี้ (Out of Scope)' with bullets citing sibling TP-keys "
            "or 'deferred' markers (see templates-task.md G12 rule).",
        )

    def _check_t16_flag_discipline(self, adf: dict, wrapper: dict | None) -> CheckResult:
        """T16: Flag Discipline for Ship-per-Merge Slices (WARN-level, Task-only, v3.13.0).

        When Task is a vertical slice (title matches Slice markers OR labels include `vs*`),
        the description SHOULD reference either:
          - a flag name matching `feat/{epic-key}/s{N}` (registered in `.flags.yaml`), or
          - an explicit "no flag (hardening)" note.

        Enforces the ship-per-merge convention (C5/C6): every slice must declare flag
        discipline at creation time so shipping pipelines know how to gate exposure.
        """
        title = (wrapper or {}).get("summary", "") or ""
        labels = (wrapper or {}).get("labels", []) or []

        is_slice = bool(SLICE_MARKER_RE.search(title)) or any(
            str(label).lower().startswith("vs") for label in labels
        )

        if not is_slice:
            return CheckResult("T16", CheckStatus.PASS, "T16 N/A (not a vertical slice)")

        body_text = extract_text(adf)
        has_flag_ref = bool(FLAG_NAME_RE.search(body_text))
        has_hardening_note = bool(HARDENING_NOTE_RE.search(body_text))

        if has_flag_ref or has_hardening_note:
            reason = "flag name referenced" if has_flag_ref else "hardening (no flag) declared"
            return CheckResult("T16", CheckStatus.PASS, f"Slice flag discipline present ({reason})")

        return CheckResult(
            "T16",
            CheckStatus.WARN,
            f"Slice title '{title[:40]}' missing flag reference or 'no flag (hardening)' note. "
            "Ship-per-merge slices MUST declare a `.flags.yaml` entry via `feat/{epic-key}/s{N}` "
            "or explicitly mark as hardening (no flag).",
            fix_hint="Add flag reference (e.g. `feat/TP-182/s1`) in description, OR add "
            "explicit 'no flag (hardening)' note. See references/flags-yaml-template.yaml.",
        )

    # ───────────────────────────────────────────────────────
    # Cross-Type Quality Checks (S7–S8, v3.16.0)
    # ───────────────────────────────────────────────────────

    def _check_s7_markdown_in_text(self, adf: dict) -> CheckResult:
        """S7: Markdown-in-text scan (ERROR, v3.16.0).

        ADF text nodes must NOT contain raw markdown syntax. Agents sometimes emit
        markdown prose (paragraph breaks, pipe-table rows, bullet prefixes, heading
        markers) inside text nodes — these render as raw literal characters in Jira,
        not as structured content.

        Patterns flagged:
          - ``\\n\\n`` sequences (paragraph break inside a text node)
          - Lines matching ``^|...|`` (pipe-markdown table rows)
          - Lines starting with ``• `` or ``- `` or ``* `` (bullet prefixes)
          - Lines starting with ``# `` through ``###### `` (markdown headings)

        Fix: replace the text node with proper ADF structural blocks
        (paragraph, bulletList, table, heading).

        See references/templates-epic.md 'ADF Text Purity' rule and
        agents/story-writer.md 'ADF Text Purity' rule card.
        """
        offending: list[str] = []

        def _scan(node: dict) -> None:
            if node.get("type") != "text" or "text" not in node:
                return
            if has_code_mark(node):
                return  # code-marked text is allowed to contain raw chars
            text = node["text"]
            local_id = node.get("localId", "")
            label = f"localId={local_id}" if local_id else f"text[:40]={text[:40]!r}"

            if MARKDOWN_IN_TEXT_PARA_BREAK_RE.search(text):
                offending.append(f"para-break in {label}")
            elif MARKDOWN_IN_TEXT_TABLE_ROW_RE.search(text):
                offending.append(f"pipe-table row in {label}")
            elif MARKDOWN_IN_TEXT_BULLET_RE.search(text):
                offending.append(f"bullet prefix in {label}")
            elif MARKDOWN_IN_TEXT_HEADING_RE.search(text):
                offending.append(f"markdown heading in {label}")

        walk_adf(adf, _scan)

        if not offending:
            return CheckResult("S7", CheckStatus.PASS, "No markdown-in-text found")

        sample = offending[:3]
        status = CheckStatus.FAIL if self.markdown_strict else CheckStatus.WARN
        return CheckResult(
            "S7",
            status,
            f"{len(offending)} text node(s) contain raw markdown syntax: {sample}. "
            "ADF text nodes must not embed markdown — use structural ADF blocks "
            "(paragraph, bulletList, table, heading, codeBlock). "
            "(v3.16.1: warn-only default; set markdown_strict=True or pass --markdown-strict to enforce; "
            "flips to ERROR default in v3.17.0)",
            fix_hint="Replace inline markdown with proper ADF nodes. "
            "See agents/story-writer.md 'ADF Text Purity' rule card and "
            "agents/adf-surgeon.md QUIRK-NEW for repair instructions.",
        )

    def _check_s8_dual_zone_ac(self, adf: dict, issue_type: str) -> CheckResult:
        """S8: Dual-Zone AC Check (ERROR/WARN, v3.16.0).

        Verifies the ``เงื่อนไขที่ต้องผ่าน`` H2 section contains two H3 subsections:
          - Business zone: heading matches S8_BUSINESS_ZONE_RE
          - Developer zone: heading matches S8_DEVELOPER_ZONE_RE

        Per-type matrix (S8_BUSINESS_ZONE_REQUIRED, S8_DEVELOPER_ZONE_REQUIRED):
          - Epic/Story/Bug: both required
          - Task: developer required; business optional (no zone check, only language)
          - Subtask: business=skip (inherits); developer required
          - QA/Chore: both optional

        Language leak check (Business zone):
          Scans business zone bullet text for banned tokens:
          SLA numbers, service names, patterns, method calls, field names.
          Always WARN regardless of strict mode.

        Strict mode (dual_zone_strict=True):
          Missing required zone → FAIL instead of WARN.
          Default: grandfather mode (warn-only). Flip to True via --dual-zone-strict.

        See references/templates-epic.md 'Dual-Zone Acceptance Criteria Convention'.
        """
        biz_required = S8_BUSINESS_ZONE_REQUIRED.get(issue_type, "optional")
        dev_required = S8_DEVELOPER_ZONE_REQUIRED.get(issue_type, "optional")

        # Both optional → pass
        if biz_required == "optional" and dev_required == "optional":
            return CheckResult("S8", CheckStatus.PASS, "S8 N/A (both zones optional for this type)")

        # Find the AC H2 section
        ac_section = get_section_content(adf, "เงื่อนไขที่ต้องผ่าน")
        if not ac_section:
            # Also try English heading
            ac_section = get_section_content(adf, "acceptance criteria")

        if not ac_section:
            if biz_required == "required" or dev_required == "required":
                missing_status = CheckStatus.FAIL if self.dual_zone_strict else CheckStatus.WARN
                return CheckResult(
                    "S8",
                    missing_status,
                    "No AC section found — cannot verify dual-zone structure. "
                    "Add H2 'เงื่อนไขที่ต้องผ่าน (Acceptance Criteria)' with Business + Developer H3 zones.",
                    fix_hint="Add AC H2 with two H3 subsections: "
                    "'Acceptance Criteria — Business' and 'Acceptance Criteria — Developer'.",
                )
            return CheckResult("S8", CheckStatus.PASS, "S8 N/A (no required AC section)")

        # Find H3 headings inside AC section
        h3_nodes = find_adf_nodes(
            {"type": "doc", "version": 1, "content": ac_section},
            lambda n: n.get("type") == "heading" and n.get("attrs", {}).get("level") == 3,
        )

        biz_zone_node: dict | None = None
        dev_zone_node: dict | None = None
        for h in h3_nodes:
            text = extract_text(h)
            if S8_BUSINESS_ZONE_RE.search(text):
                biz_zone_node = h
            if S8_DEVELOPER_ZONE_RE.search(text):
                dev_zone_node = h

        issues: list[str] = []
        missing_status = CheckStatus.FAIL if self.dual_zone_strict else CheckStatus.WARN

        if biz_required == "required" and biz_zone_node is None:
            issues.append(
                f"Missing Business AC zone (H3 'Acceptance Criteria — Business') — required for {issue_type}"
            )
        if dev_required == "required" and dev_zone_node is None:
            issues.append(
                f"Missing Developer AC zone (H3 'Acceptance Criteria — Developer') — required for {issue_type}"
            )

        if issues:
            return CheckResult(
                "S8",
                missing_status,
                f"Dual-zone AC incomplete: {'; '.join(issues)}. "
                "See references/templates-epic.md 'Dual-Zone Acceptance Criteria Convention'.",
                fix_hint="Add missing H3 zone(s) under the AC H2. "
                "Business zone: observable outcomes only. Developer zone: testable specs with SLA/service/GWT.",
            )

        # Language leak check: business zone must not contain banned jargon.
        if biz_zone_node is not None:
            # Extract text between business H3 and next H3/H2
            biz_text = ""
            in_biz = False
            for node in ac_section:
                if node is biz_zone_node:
                    in_biz = True
                    continue
                if in_biz and node.get("type") == "heading":
                    break
                if in_biz:
                    biz_text += extract_text(node) + " "

            leaks: list[str] = []
            if S8_BANNED_SLA_RE.search(biz_text):
                leaks.append("SLA number (e.g. '30s', 'p95')")
            if S8_BANNED_SERVICE_RE.search(biz_text):
                leaks.append("service name (Pusher/S3/Redis/Kafka/…)")
            if S8_BANNED_PATTERN_RE.search(biz_text):
                leaks.append("pattern name (async/retry/debounce/…)")
            if S8_BANNED_METHOD_RE.search(biz_text):
                leaks.append("method call (ClassName.method())")
            if S8_BANNED_FIELD_RE.search(biz_text):
                leaks.append("field name (customfield_NNNNN)")

            if leaks:
                return CheckResult(
                    "S8",
                    CheckStatus.WARN,
                    f"Business AC zone contains tech jargon: {leaks}. "
                    "Business zone must use observable outcomes only — move technical detail to Developer zone.",
                    fix_hint="Remove banned tokens from Business AC zone. "
                    "Allowed: user-observable outcomes. "
                    "Move SLA/service/pattern details to Developer AC zone.",
                )

        return CheckResult("S8", CheckStatus.PASS, "Dual-zone AC structure valid")

    # ───────────────────────────────────────────────────────
    # Story Quality Checks (S1–S6)
    # ───────────────────────────────────────────────────────

    def _check_s1_invest(self, _secs: dict) -> CheckResult:
        """S1: INVEST — Small (<=5 AC panels), Testable (GWT in ACs)."""
        ac_section = _secs.get("acceptance criteria", [])
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

    def _check_s2_narrative(self, _secs: dict, adf: dict) -> CheckResult:
        """S2: User Story narrative — As a / I want / So that."""
        story_section = _secs.get("user story") or _secs.get("narrative")
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

    def _check_s3_anti_patterns(self, _secs: dict) -> CheckResult:
        """S3: Narrative anti-patterns — generic persona, solution masking, missing why."""
        story_section = _secs.get("user story") or _secs.get("narrative")
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

    def _check_s4_acceptance_criteria(self, _secs: dict) -> CheckResult:
        """S4: AC format — panels with Given/When/Then, correct panel types."""
        ac_section = _secs.get("acceptance criteria", [])
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

    def _check_s5_scope(self, adf: dict, _secs: dict) -> CheckResult:
        """S5: Scope definition — services impacted, in/out scope."""
        scope_section = _secs.get("scope", [])
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

    def _check_st1_objective(self, _secs: dict) -> CheckResult:
        """ST1: Clear 1-2 sentence objective."""
        obj_section = _secs.get("objective", [])
        if not obj_section:
            return CheckResult("ST1", CheckStatus.FAIL, "No Objective section found")

        text = extract_text(obj_section).strip()
        if not text:
            return CheckResult("ST1", CheckStatus.FAIL, "Objective section is empty")
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
        if len(sentences) > 3:
            return CheckResult("ST1", CheckStatus.WARN, "Objective too long (>3 sentences)")
        return CheckResult("ST1", CheckStatus.PASS, "Objective OK")

    def _check_st2_scope_files(self, _secs: dict) -> CheckResult:
        """ST2: Scope & Files — tables with real file paths."""
        scope_section = _secs.get("scope", [])
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

    def _check_st3_acceptance_criteria(self, _secs: dict) -> CheckResult:
        """ST3: AC format — Given/When/Then in panels."""
        ac_section = _secs.get("acceptance criteria", [])
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
        del adf
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

    def _check_e1_vision(self, _secs: dict) -> CheckResult:
        """E1: Vision — Epic Overview section with clear problem statement."""
        overview = _secs.get("epic overview") or _secs.get("overview")
        if not overview:
            return CheckResult("E1", CheckStatus.FAIL, "No Epic Overview section found")

        text = extract_text(overview).strip()
        if len(text.split()) < 5:
            return CheckResult("E1", CheckStatus.WARN, "Epic Overview too brief")
        return CheckResult("E1", CheckStatus.PASS, "Epic Overview present")

    def _check_e2_rice(self, _secs: dict) -> CheckResult:
        """E2: RICE Score — table with Reach/Impact/Confidence/Effort."""
        rice_section = _secs.get("rice", [])
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

    def _check_e3_scope(self, _secs: dict) -> CheckResult:
        """E3: Scope — features listed with must-have/should-have."""
        scope_section = _secs.get("scope", [])
        if not scope_section:
            return CheckResult("E3", CheckStatus.FAIL, "No Scope section found")

        text = extract_text(scope_section)
        if len(text.split()) < 10:
            return CheckResult("E3", CheckStatus.WARN, "Scope section too brief")
        return CheckResult("E3", CheckStatus.PASS, "Scope section present")

    def _check_e4_stories(self, _secs: dict) -> CheckResult:
        """E4: User Stories — draft stories identified."""
        stories_section = _secs.get("user stories") or _secs.get("stories")
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

    def _check_qa1_coverage(self, _secs: dict) -> CheckResult:
        """QA1: Coverage — AC Coverage table exists."""
        coverage = _secs.get("ac coverage") or _secs.get("coverage")
        if not coverage:
            return CheckResult("QA1", CheckStatus.FAIL, "No AC Coverage section found")

        tables = find_adf_nodes(coverage, lambda n: n.get("type") == "table")
        if not tables:
            return CheckResult("QA1", CheckStatus.WARN, "AC Coverage has no table")
        return CheckResult("QA1", CheckStatus.PASS, "AC Coverage table present")

    def _check_qa2_test_format(self, _secs: dict) -> CheckResult:
        """QA2: Test format — test cases have Given/When/Then."""
        tc_section = _secs.get("test cases") or _secs.get("test")
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

    def _check_qa3_scenarios(self, _secs: dict) -> CheckResult:
        """QA3: Scenarios — grouped by type with correct panel colors."""
        tc_section = _secs.get("test cases", [])
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

    def _check_tk1_context(self, _secs: dict) -> CheckResult:
        """TK1: Context — problem/reason section explaining why this task exists."""
        context_section = _secs.get("context") or _secs.get("objective") or _secs.get("bug description")
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

    def _check_tk3_acceptance(self, _secs: dict) -> CheckResult:
        """TK3: Acceptance criteria — table or list of done criteria."""
        ac_section = _secs.get("acceptance criteria") or _secs.get("done criteria") or _secs.get("fix criteria")

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
