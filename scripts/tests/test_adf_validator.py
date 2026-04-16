"""Tests for lib/adf_validator.py — ADF quality gate engine.

Covers: data classes, ADF utilities, technical checks (T1-T5),
story checks (S1-S6), subtask checks (ST1-ST5), auto-fix, and integration.
"""

import sys
from pathlib import Path

import pytest

# Add parent dir so lib imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.adf_validator import (
    VALID_PANEL_TYPES,
    AdfValidator,
    CheckResult,
    CheckStatus,
    ValidationReport,
    detect_format,
    extract_text,
    find_adf_nodes,
    find_headings,
    get_section_content,
    has_code_mark,
    has_link_mark,
    walk_adf,
)

# ═══════════════════════════════════════════════════════════
# Fixtures — reusable ADF building blocks
# ═══════════════════════════════════════════════════════════


def _text(s: str, marks=None) -> dict:
    node = {"type": "text", "text": s}
    if marks:
        node["marks"] = marks
    return node


def _paragraph(*texts) -> dict:
    return {"type": "paragraph", "content": list(texts)}


def _heading(text: str, level: int = 2) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [_text(text)],
    }


def _panel(panel_type: str, *content) -> dict:
    return {
        "type": "panel",
        "attrs": {"panelType": panel_type},
        "content": list(content),
    }


def _doc(*content) -> dict:
    return {"type": "doc", "version": 1, "content": list(content)}


def _gwt_paragraph(given="Given: X", when="When: Y", then="Then: Z") -> dict:
    return _paragraph(_text(f"{given}\n{when}\n{then}"))


def _thai_paragraph() -> dict:
    # "User can log in" — Thai text required for T4 Thai language validation check
    return _paragraph(_text("ผู้ใช้สามารถเข้าสู่ระบบได้"))


def _ac_panel_gwt(label="AC1", given="Given: X", when="When: Y", then="Then: Z") -> dict:
    return _panel("success", _paragraph(_text(f"**{label}**\n{given}\n{when}\n{then}")))


def _story_adf(num_acs=2, thai=True, narrative=True, scope=True) -> dict:
    """Build a valid story ADF for testing."""
    content = []

    if narrative:
        content.append(_heading("User Story"))
        content.append(
            # "As a merchant I want to manage coupons So that increase sales"
            _panel("info", _paragraph(_text("As a ร้านค้า I want to จัดการคูปอง So that เพิ่มยอดขาย")))
        )

    content.append(_heading("Acceptance Criteria"))
    for i in range(num_acs):
        content.append(_ac_panel_gwt(f"AC{i + 1}"))

    if scope:
        content.append(_heading("Scope"))
        content.append(
            _panel("note", _paragraph(_text("In-scope: "), _text("src/modules/coupon/", marks=[{"type": "code"}])))
        )

    content.append(_heading("Reference"))
    content.append(
        _paragraph(
            _text("Parent: "),
            _text("TEST-1200", marks=[{"type": "link", "attrs": {"href": "https://jira/TEST-1200"}}]),
        )
    )

    if thai:
        content.append(_thai_paragraph())

    return _doc(*content)


def _subtask_adf(tag="[BE]", thai=True) -> dict:
    """Build a valid subtask ADF for testing."""
    content = [
        _heading("Objective"),
        # "Create API endpoint for coupon management"
        _panel("info", _paragraph(_text("สร้าง API endpoint สำหรับจัดการคูปอง"))),
        _heading("Scope & Files"),
        _panel(
            "note",
            _paragraph(
                _text("src/modules/coupon/coupon.service.ts", marks=[{"type": "code"}]),
            ),
        ),
        _heading("Acceptance Criteria"),
        # "Given: has coupon / When: call API / Then: get response 200"
        _panel("success", _paragraph(_text("Given: มี coupon\nWhen: เรียก API\nThen: ได้ response 200"))),
        _heading("Reference"),
        _paragraph(
            _text("Parent: "),
            _text("TEST-1200", marks=[{"type": "link", "attrs": {"href": "#"}}]),
        ),
    ]
    if thai:
        content.append(_thai_paragraph())
    return _doc(*content)


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════


class TestCheckStatus:
    def test_values(self):
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.WARN.value == "warn"
        assert CheckStatus.FAIL.value == "fail"


class TestCheckResult:
    def test_basic(self):
        r = CheckResult("T1", CheckStatus.PASS, "OK")
        assert r.check_id == "T1"
        assert r.status == CheckStatus.PASS
        assert r.message == "OK"
        assert r.fix_hint == ""
        assert r.auto_fixable is False

    def test_with_fix_hint(self):
        r = CheckResult("T2", CheckStatus.FAIL, "Bad", fix_hint="Fix it", auto_fixable=True)
        assert r.auto_fixable is True
        assert r.fix_hint == "Fix it"


class TestValidationReport:
    def test_empty_report(self):
        report = ValidationReport(issue_type="story")
        assert report.score == 0.0
        assert report.passed is False

    def test_all_pass(self):
        report = ValidationReport(issue_type="story")
        report.checks = [
            CheckResult("T1", CheckStatus.PASS, "OK"),
            CheckResult("T2", CheckStatus.PASS, "OK"),
        ]
        assert report.score == 100.0
        assert report.passed is True

    def test_mixed_scores(self):
        report = ValidationReport(issue_type="story")
        report.checks = [
            CheckResult("T1", CheckStatus.PASS, "OK"),  # 1.0
            CheckResult("T2", CheckStatus.WARN, "Warn"),  # 0.5
            CheckResult("T3", CheckStatus.FAIL, "Bad"),  # 0.0
        ]
        # (1.0 + 0.5 + 0.0) / 3 * 100 = 50.0
        assert report.score == pytest.approx(50.0)
        assert report.passed is False

    def test_threshold_boundary(self):
        # 9 pass + 1 warn = (9 + 0.5) / 10 * 100 = 95%
        report = ValidationReport(issue_type="story")
        report.checks = [CheckResult(f"C{i}", CheckStatus.PASS, "OK") for i in range(9)]
        report.checks.append(CheckResult("C9", CheckStatus.WARN, "Warn"))
        assert report.score == pytest.approx(95.0)
        assert report.passed is True

    def test_threshold_fail(self):
        # 8 pass + 2 fail = (8 + 0) / 10 * 100 = 80%
        report = ValidationReport(issue_type="story")
        report.checks = [CheckResult(f"C{i}", CheckStatus.PASS, "OK") for i in range(8)]
        report.checks.extend(
            [
                CheckResult("C8", CheckStatus.FAIL, "Bad"),
                CheckResult("C9", CheckStatus.FAIL, "Bad"),
            ]
        )
        assert report.score == pytest.approx(80.0)
        assert report.passed is False

    def test_to_dict(self):
        report = ValidationReport(issue_type="subtask")
        report.checks = [
            CheckResult("T1", CheckStatus.PASS, "OK"),
            CheckResult("T2", CheckStatus.WARN, "Warn"),
            CheckResult("T3", CheckStatus.FAIL, "Bad", fix_hint="Fix it"),
        ]
        d = report.to_dict()
        assert d["issue_type"] == "subtask"
        assert d["total_checks"] == 3
        assert d["passed"] == 1
        assert d["warned"] == 1
        assert d["failed"] == 1
        # issues only include non-PASS
        assert len(d["issues"]) == 2
        assert d["issues"][0]["id"] == "T2"
        assert d["issues"][1]["id"] == "T3"
        assert d["issues"][1]["fix_hint"] == "Fix it"


# ═══════════════════════════════════════════════════════════
# ADF Utilities
# ═══════════════════════════════════════════════════════════


class TestWalkAdf:
    def test_flat_doc(self):
        doc = _doc(_paragraph(_text("hello")))
        visited = []
        walk_adf(doc, lambda n: visited.append(n.get("type")))
        assert "doc" in visited
        assert "paragraph" in visited
        assert "text" in visited

    def test_does_not_walk_attrs(self):
        """walk_adf should NOT descend into attrs objects."""
        node = {
            "type": "panel",
            "attrs": {"panelType": "info", "nested": {"type": "shouldNotVisit"}},
            "content": [_text("hello")],
        }
        types = []
        walk_adf(node, lambda n: types.append(n.get("type")))
        assert "shouldNotVisit" not in types
        assert "panel" in types
        assert "text" in types

    def test_walk_list(self):
        nodes = [_text("a"), _text("b")]
        texts = []
        walk_adf(nodes, lambda n: texts.append(n.get("text", "")))
        assert texts == ["a", "b"]


class TestFindAdfNodes:
    def test_find_panels(self):
        doc = _doc(
            _panel("info", _paragraph(_text("a"))),
            _paragraph(_text("b")),
            _panel("success", _paragraph(_text("c"))),
        )
        panels = find_adf_nodes(doc, lambda n: n.get("type") == "panel")
        assert len(panels) == 2

    def test_find_none(self):
        doc = _doc(_paragraph(_text("no panels here")))
        panels = find_adf_nodes(doc, lambda n: n.get("type") == "panel")
        assert panels == []


class TestExtractText:
    def test_simple(self):
        doc = _doc(_paragraph(_text("hello"), _text(" world")))
        assert extract_text(doc) == "hello  world"

    def test_nested(self):
        doc = _doc(
            _panel("info", _paragraph(_text("inside panel"))),
            _paragraph(_text("outside")),
        )
        text = extract_text(doc)
        assert "inside panel" in text
        assert "outside" in text

    def test_empty(self):
        doc = _doc()
        assert extract_text(doc) == ""


class TestFindHeadings:
    def test_all_headings(self):
        doc = _doc(_heading("H2", 2), _heading("H3", 3), _heading("H2b", 2))
        assert len(find_headings(doc)) == 3

    def test_filter_by_level(self):
        doc = _doc(_heading("H2", 2), _heading("H3", 3))
        h3s = find_headings(doc, level=3)
        assert len(h3s) == 1
        assert extract_text(h3s[0]) == "H3"


class TestGetSectionContent:
    def test_section_between_headings(self):
        doc = _doc(
            _heading("Intro", 2),
            _paragraph(_text("intro text")),
            _heading("Acceptance Criteria", 2),
            _paragraph(_text("ac text")),
            _panel("success", _paragraph(_text("gwt"))),
            _heading("Other", 2),
            _paragraph(_text("other text")),
        )
        section = get_section_content(doc, "acceptance criteria")
        assert len(section) == 2  # paragraph + panel
        text = extract_text(section)
        assert "ac text" in text
        assert "other text" not in text

    def test_section_not_found(self):
        doc = _doc(_heading("Intro", 2), _paragraph(_text("text")))
        assert get_section_content(doc, "nonexistent") == []


class TestHasCodeMark:
    def test_with_code(self):
        node = _text("path", marks=[{"type": "code"}])
        assert has_code_mark(node) is True

    def test_without_code(self):
        assert has_code_mark(_text("plain")) is False

    def test_with_other_marks(self):
        node = _text("bold", marks=[{"type": "strong"}])
        assert has_code_mark(node) is False


class TestHasLinkMark:
    def test_with_link(self):
        node = _text("url", marks=[{"type": "link", "attrs": {"href": "#"}}])
        assert has_link_mark(node) is True

    def test_without_link(self):
        assert has_link_mark(_text("plain")) is False


class TestDetectFormat:
    def test_raw_adf(self):
        doc = _doc(_paragraph(_text("hello")))
        fmt, adf = detect_format(doc)
        assert fmt == "raw"
        assert adf is doc

    def test_create_format(self):
        wrapper = {
            "projectKey": "TEST",
            "type": "Story",
            "summary": "Test",
            "description": _doc(_paragraph(_text("desc"))),
        }
        fmt, adf = detect_format(wrapper)
        assert fmt == "create"
        assert adf.get("type") == "doc"

    def test_edit_format(self):
        wrapper = {
            "issues": ["TEST-1234"],
            "description": _doc(_paragraph(_text("desc"))),
        }
        fmt, adf = detect_format(wrapper)
        assert fmt == "edit"
        assert adf.get("type") == "doc"

    def test_unknown_with_description(self):
        data = {"description": _doc(_paragraph(_text("x")))}
        fmt, adf = detect_format(data)
        assert fmt == "unknown"
        assert adf.get("type") == "doc"

    def test_unknown_no_description(self):
        fmt, adf = detect_format({"foo": "bar"})
        assert fmt == "unknown"


# ═══════════════════════════════════════════════════════════
# Technical Checks (T1-T5)
# ═══════════════════════════════════════════════════════════


class TestT1AdfFormat:
    def setup_method(self):
        self.v = AdfValidator()

    def test_valid(self):
        r = self.v._check_t1_adf_format(_doc(_paragraph(_text("x"))))
        assert r.status == CheckStatus.PASS

    def test_missing_type(self):
        r = self.v._check_t1_adf_format({"version": 1, "content": []})
        assert r.status == CheckStatus.FAIL
        assert "type" in r.message

    def test_wrong_version(self):
        r = self.v._check_t1_adf_format({"type": "doc", "version": 2, "content": [{}]})
        assert r.status == CheckStatus.FAIL
        assert "version" in r.message

    def test_empty_content(self):
        r = self.v._check_t1_adf_format({"type": "doc", "version": 1, "content": []})
        assert r.status == CheckStatus.FAIL


class TestT2Panels:
    def setup_method(self):
        self.v = AdfValidator()

    def test_valid_panels(self):
        doc = _doc(_panel("info", _paragraph(_text("x"))))
        r = self.v._check_t2_panels(doc)
        assert r.status == CheckStatus.PASS

    def test_no_panels(self):
        doc = _doc(_paragraph(_text("no panels")))
        r = self.v._check_t2_panels(doc)
        assert r.status == CheckStatus.WARN

    def test_invalid_panel_type(self):
        doc = _doc({"type": "panel", "attrs": {"panelType": "invalid"}, "content": [_paragraph(_text("x"))]})
        r = self.v._check_t2_panels(doc)
        assert r.status == CheckStatus.FAIL
        assert r.auto_fixable is True


class TestT3InlineCode:
    def setup_method(self):
        self.v = AdfValidator()

    def test_all_marked(self):
        doc = _doc(
            _paragraph(
                _text("Check "),
                _text("src/main.ts", marks=[{"type": "code"}]),
            )
        )
        r = self.v._check_t3_inline_code(doc)
        assert r.status == CheckStatus.PASS

    def test_unmarked_file_path(self):
        doc = _doc(_paragraph(_text("Edit src/modules/coupon/service.ts please")))
        r = self.v._check_t3_inline_code(doc)
        assert r.status in (CheckStatus.WARN, CheckStatus.FAIL)

    def test_no_technical_terms(self):
        doc = _doc(_paragraph(_text("Just plain text without paths")))
        r = self.v._check_t3_inline_code(doc)
        assert r.status == CheckStatus.PASS


class TestT5RequiredFields:
    def setup_method(self):
        self.v = AdfValidator()

    def test_create_all_fields(self):
        wrapper = {
            "projectKey": "TEST",
            "type": "Story",
            "summary": "Test",
            "description": _doc(_paragraph(_text("x"))),
        }
        r = self.v._check_t5_required_fields(_doc(), "story", wrapper)
        assert r.status == CheckStatus.PASS

    def test_create_missing_summary(self):
        wrapper = {"projectKey": "TEST", "type": "Story", "description": _doc()}
        r = self.v._check_t5_required_fields(_doc(), "story", wrapper)
        assert r.status == CheckStatus.FAIL
        assert "summary" in r.message

    def test_edit_valid(self):
        wrapper = {"issues": ["TEST-1234"], "description": _doc(_paragraph(_text("x")))}
        r = self.v._check_t5_required_fields(_doc(), "subtask", wrapper)
        assert r.status == CheckStatus.PASS

    def test_edit_forbidden_fields(self):
        wrapper = {"issues": ["TEST-1234"], "description": _doc(), "summary": "oops"}
        r = self.v._check_t5_required_fields(_doc(), "subtask", wrapper)
        assert r.status == CheckStatus.FAIL
        assert "forbidden" in r.message

    def test_no_wrapper(self):
        r = self.v._check_t5_required_fields(_doc(_paragraph(_text("x"))), "story", None)
        assert r.status == CheckStatus.PASS


# ═══════════════════════════════════════════════════════════
# Story Checks (S1-S6)
# ═══════════════════════════════════════════════════════════


class TestS1Invest:
    def setup_method(self):
        self.v = AdfValidator()

    def test_valid_acs(self):
        adf = _story_adf(num_acs=2)
        r = self.v._check_s1_invest(self.v._extract_sections(adf))
        assert r.status == CheckStatus.PASS

    def test_too_many_acs(self):
        adf = _story_adf(num_acs=6)
        r = self.v._check_s1_invest(self.v._extract_sections(adf))
        assert r.status == CheckStatus.WARN
        assert "6" in r.message

    def test_no_acs(self):
        adf = _doc(_heading("Acceptance Criteria"))
        r = self.v._check_s1_invest(self.v._extract_sections(adf))
        assert r.status == CheckStatus.FAIL


class TestS2Narrative:
    def setup_method(self):
        self.v = AdfValidator()

    def test_valid_narrative(self):
        adf = _story_adf()
        r = self.v._check_s2_narrative(self.v._extract_sections(adf), adf)
        assert r.status == CheckStatus.PASS

    def test_missing_narrative(self):
        adf = _doc(_heading("Other"), _paragraph(_text("no narrative")))
        r = self.v._check_s2_narrative(self.v._extract_sections(adf), adf)
        assert r.status == CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# Subtask Checks
# ═══════════════════════════════════════════════════════════


class TestST4TagSummary:
    def setup_method(self):
        self.v = AdfValidator()

    def test_valid_tag(self):
        wrapper = {"projectKey": "TEST", "type": "Sub-task", "summary": "[BE] Create coupon API"}
        r = self.v._check_st4_tag_summary(_subtask_adf(), wrapper)
        assert r.status == CheckStatus.PASS

    def test_missing_tag(self):
        wrapper = {"projectKey": "TEST", "type": "Sub-task", "summary": "Create coupon API"}
        r = self.v._check_st4_tag_summary(_subtask_adf(), wrapper)
        assert r.status == CheckStatus.FAIL

    def test_edit_format_ok(self):
        """EDIT format has no summary — should PASS (set at creation time)."""
        wrapper = {"issues": ["TEST-1234"], "description": _subtask_adf()}
        r = self.v._check_st4_tag_summary(_subtask_adf(), wrapper)
        assert r.status == CheckStatus.PASS

    def test_no_wrapper(self):
        r = self.v._check_st4_tag_summary(_subtask_adf(), None)
        assert r.status == CheckStatus.WARN


# ═══════════════════════════════════════════════════════════
# Auto-Fix
# ═══════════════════════════════════════════════════════════


class TestAutoFix:
    def setup_method(self):
        self.v = AdfValidator()

    def test_fix_panel_types(self):
        doc = _doc(
            {"type": "panel", "attrs": {"panelType": "highlight"}, "content": [_paragraph(_text("x"))]},
            _panel("info", _paragraph(_text("y"))),
        )
        report = self.v.validate(doc, "story")
        fixed, new_report = self.v.auto_fix(doc, report)

        # Check the fix was applied
        panels = find_adf_nodes(fixed, lambda n: n.get("type") == "panel")
        panel_types = {p["attrs"]["panelType"] for p in panels}
        assert panel_types <= VALID_PANEL_TYPES

    def test_fix_code_marks(self):
        doc = _doc(
            _paragraph(_text("Edit src/modules/coupon/service.ts file")),
            _paragraph(_text("Also /api/v1/coupons route")),
        )
        count = self.v._fix_code_marks(doc)
        assert count >= 1

        # Verify marks were added
        marked = find_adf_nodes(doc, lambda n: n.get("type") == "text" and has_code_mark(n))
        assert len(marked) >= 1

    def test_auto_fix_does_not_mutate_original(self):
        doc = _doc(
            {"type": "panel", "attrs": {"panelType": "highlight"}, "content": [_paragraph(_text("x"))]},
        )
        report = self.v.validate(doc, "story")
        original_type = doc["content"][0]["attrs"]["panelType"]
        fixed, _ = self.v.auto_fix(doc, report)
        assert doc["content"][0]["attrs"]["panelType"] == original_type  # unchanged


# ═══════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════


class TestFullValidation:
    def setup_method(self):
        self.v = AdfValidator()

    def test_valid_story_passes(self):
        adf = _story_adf(num_acs=2, thai=True)
        report = self.v.validate(adf, "story")
        assert report.score >= 90.0
        assert report.passed is True
        assert len(report.checks) == 11  # T1-T5 + S1-S6

    def test_valid_subtask_passes(self):
        adf = _subtask_adf()
        wrapper = {
            "projectKey": "TEST",
            "type": "Sub-task",
            "summary": "[BE] Create coupon API",
            "description": adf,
        }
        report = self.v.validate(adf, "subtask", wrapper)
        assert report.score >= 90.0
        assert report.passed is True
        assert len(report.checks) == 10  # T1-T5 + ST1-ST5

    def test_empty_doc_fails(self):
        adf = {"type": "doc", "version": 1, "content": []}
        report = self.v.validate(adf, "story")
        assert report.passed is False
        # T1 should fail (empty content)
        t1 = next(c for c in report.checks if c.check_id == "T1")
        assert t1.status == CheckStatus.FAIL

    # ───────────────────────────────────────────────────────
    # T6: Title Ambiguity Scan (v3.12.0)
    # ───────────────────────────────────────────────────────

    def test_t6_ambiguous_title_without_disambiguation_section_warns(self):
        adf = _doc(_paragraph(_text("ระบบ billboard owners")))
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "Review flow — notification trigger",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t6 = next(c for c in report.checks if c.check_id == "T6")
        assert t6.status == CheckStatus.WARN
        assert "review" in t6.message.lower()
        assert "trigger" in t6.message.lower()

    def test_t6_unambiguous_title_passes(self):
        adf = _doc(_paragraph(_text("ระบบ export CSV")))
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "Billboard owner dashboard — export CSV",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t6 = next(c for c in report.checks if c.check_id == "T6")
        assert t6.status == CheckStatus.PASS

    def test_t6_ambiguous_title_with_disambiguation_section_passes(self):
        adf = _doc(
            _heading("Scope Disambiguation"),
            _paragraph(_text("QA-review trigger interpretation")),
        )
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "Review flow — notification trigger",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t6 = next(c for c in report.checks if c.check_id == "T6")
        assert t6.status == CheckStatus.PASS

    def test_t6_only_runs_for_epic_and_task(self):
        adf = _doc(_paragraph(_text("x")))
        for t in ("story", "subtask", "qa"):
            report = self.v.validate(adf, t)
            assert all(c.check_id != "T6" for c in report.checks), f"{t} should not have T6"
        for t in ("epic", "task"):
            report = self.v.validate(adf, t)
            assert any(c.check_id == "T6" for c in report.checks), f"{t} should have T6"

    def test_t6_never_fails_only_warns(self):
        """T6 is documented as WARN-level; verify no FAIL path exists."""
        adf = _doc(_paragraph(_text("review handle process trigger " * 20)))
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "review handle process trigger send notify update check",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t6 = next(c for c in report.checks if c.check_id == "T6")
        assert t6.status != CheckStatus.FAIL

    def test_story_check_count(self):
        report = self.v.validate(_doc(_paragraph(_text("x"))), "story")
        assert len(report.checks) == 11

    def test_subtask_check_count(self):
        report = self.v.validate(_doc(_paragraph(_text("x"))), "subtask")
        assert len(report.checks) == 10

    def test_epic_check_count(self):
        report = self.v.validate(_doc(_paragraph(_text("x"))), "epic")
        # v3.12.2: T10 (explicit Jira links), T12 (paired-epic regression),
        # T13 (code reference), T14 (vague AC phrases) added for Epic.
        # T11 + T15 are Task-only. T9 is Epic-only.
        # T1-T10 + T12-T14 + E1-E4 = 17.
        assert len(report.checks) == 17

    def test_task_check_count(self):
        report = self.v.validate(_doc(_paragraph(_text("x"))), "task")
        # v3.12.2: T10, T12, T13, T14 + T11 (Estimate), T15 (Out of Scope) added for Task.
        # T9 is Epic-only. T1-T8 + T10-T15 + TK1-TK4 = 18.
        assert len(report.checks) == 18

    def test_qa_check_count(self):
        report = self.v.validate(_doc(_paragraph(_text("x"))), "qa")
        assert len(report.checks) == 10

    def test_unknown_type_only_technical(self):
        report = self.v.validate(_doc(_paragraph(_text("x"))), "unknown")
        assert len(report.checks) == 5  # T1-T5 only

    def test_to_dict_roundtrip(self):
        adf = _story_adf()
        report = self.v.validate(adf, "story")
        d = report.to_dict()
        assert isinstance(d["score"], float)
        assert isinstance(d["issues"], list)
        assert d["total_checks"] == 11
        assert d["passed"] + d["warned"] + d["failed"] == d["total_checks"]


# ═══════════════════════════════════════════════════════════
# T7: Canonical Scope Disambiguation Heading (v3.12.1 — G1)
# ═══════════════════════════════════════════════════════════


class TestT7CanonicalDisambig:
    def setup_method(self):
        self.v = AdfValidator()

    def test_title_without_cues_passes_na(self):
        """Title with <2 cue words → T7 N/A (PASS)."""
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Epic", "summary": "Export CSV dashboard", "description": adf}
        report = self.v.validate(adf, "epic", wrapper)
        t7 = next(c for c in report.checks if c.check_id == "T7")
        assert t7.status == CheckStatus.PASS
        assert "N/A" in t7.message

    def test_canonical_heading_passes(self):
        adf = _doc(
            _heading("Scope Disambiguation", 2),
            _paragraph(_text("interpretation")),
        )
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "Review flow — notification trigger",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t7 = next(c for c in report.checks if c.check_id == "T7")
        assert t7.status == CheckStatus.PASS

    def test_canonical_heading_with_th_subtitle_passes(self):
        """Canonical heading allows `—` or `:` subtitle separator."""
        adf = _doc(_heading("Scope Disambiguation — การทบทวน AI", 2))
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "Review flow — notification trigger",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t7 = next(c for c in report.checks if c.check_id == "T7")
        assert t7.status == CheckStatus.PASS

    def test_near_miss_heading_warns(self):
        adf = _doc(_heading("Scope Clarification", 2))
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "Review flow — notification trigger",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t7 = next(c for c in report.checks if c.check_id == "T7")
        assert t7.status == CheckStatus.WARN
        assert "near-miss" in t7.message.lower() or "canonical" in t7.message.lower()

    def test_missing_heading_when_cues_present_warns(self):
        adf = _doc(_paragraph(_text("nothing")))
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "Review flow — notification trigger",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t7 = next(c for c in report.checks if c.check_id == "T7")
        assert t7.status == CheckStatus.WARN
        assert "canonical" in t7.message.lower()

    def test_t7_never_fails(self):
        """T7 is WARN-only — never FAIL."""
        adf = _doc(_heading("Something Entirely Different", 2))
        wrapper = {
            "projectKey": "TP",
            "type": "Epic",
            "summary": "review trigger process handle",
            "description": adf,
        }
        report = self.v.validate(adf, "epic", wrapper)
        t7 = next(c for c in report.checks if c.check_id == "T7")
        assert t7.status != CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T8: Decision-Path Qualifier (v3.12.1 — G3)
# ═══════════════════════════════════════════════════════════


class TestT8DecisionPathQualifier:
    def setup_method(self):
        self.v = AdfValidator()

    def test_no_decision_verb_passes(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "Add CSV export", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t8 = next(c for c in report.checks if c.check_id == "T8")
        assert t8.status == CheckStatus.PASS

    def test_thai_qualified_passes(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "AI auto-อนุมัติสื่อ", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t8 = next(c for c in report.checks if c.check_id == "T8")
        assert t8.status == CheckStatus.PASS

    def test_thai_unqualified_warns(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "AI อนุมัติสื่อ", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t8 = next(c for c in report.checks if c.check_id == "T8")
        assert t8.status == CheckStatus.WARN
        assert "อนุมัติ" in t8.message

    def test_english_unqualified_warns(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "Admin approve media", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t8 = next(c for c in report.checks if c.check_id == "T8")
        assert t8.status == CheckStatus.WARN

    def test_english_qualified_passes(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Admin manual-approve media",
            "description": adf,
        }
        report = self.v.validate(adf, "task", wrapper)
        t8 = next(c for c in report.checks if c.check_id == "T8")
        assert t8.status == CheckStatus.PASS

    def test_t8_never_fails(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "approve reject decide", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t8 = next(c for c in report.checks if c.check_id == "T8")
        assert t8.status != CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T9: Bilateral Epic Reference (v3.12.1 — G6)
# ═══════════════════════════════════════════════════════════


class TestT9BilateralEpicRef:
    def setup_method(self):
        self.v = AdfValidator()

    def test_no_inline_card_passes(self):
        adf = _doc(_paragraph(_text("no refs")))
        wrapper = {"projectKey": "TP", "type": "Epic", "summary": "Solo epic", "description": adf}
        report = self.v.validate(adf, "epic", wrapper)
        t9 = next(c for c in report.checks if c.check_id == "T9")
        assert t9.status == CheckStatus.PASS

    def test_inline_card_without_matrix_warns(self):
        adf = _doc(
            _paragraph(
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-183"}},
            ),
        )
        wrapper = {"projectKey": "TP", "type": "Epic", "summary": "Linked epic", "description": adf}
        report = self.v.validate(adf, "epic", wrapper)
        t9 = next(c for c in report.checks if c.check_id == "T9")
        assert t9.status == CheckStatus.WARN
        assert "TP-183" in t9.message

    def test_inline_card_with_matrix_and_related_column_passes(self):
        adf = _doc(
            _paragraph(
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-183"}},
            ),
            _heading("Coverage Matrix", 3),
            _paragraph(_text("Scenario | This Epic | Related Epic(s) | Out of Scope")),
            _paragraph(_text("path | ✅ | TP-183 | —")),
        )
        wrapper = {"projectKey": "TP", "type": "Epic", "summary": "Linked epic", "description": adf}
        report = self.v.validate(adf, "epic", wrapper)
        t9 = next(c for c in report.checks if c.check_id == "T9")
        assert t9.status == CheckStatus.PASS

    def test_inline_card_with_matrix_missing_related_column_warns(self):
        adf = _doc(
            _paragraph(
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-183"}},
            ),
            _heading("Coverage Matrix", 3),
            _paragraph(_text("Scenario | This Epic | Out of Scope")),
        )
        wrapper = {"projectKey": "TP", "type": "Epic", "summary": "Linked epic", "description": adf}
        report = self.v.validate(adf, "epic", wrapper)
        t9 = next(c for c in report.checks if c.check_id == "T9")
        assert t9.status == CheckStatus.WARN

    def test_t9_only_runs_for_epic(self):
        adf = _doc(
            _paragraph(
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-183"}},
            ),
        )
        # Task should NOT have T9
        report = self.v.validate(adf, "task", {"projectKey": "TP", "type": "Task", "summary": "x"})
        assert all(c.check_id != "T9" for c in report.checks)
        # Epic should have T9
        report = self.v.validate(adf, "epic", {"projectKey": "TP", "type": "Epic", "summary": "x"})
        assert any(c.check_id == "T9" for c in report.checks)

    def test_t9_never_fails(self):
        adf = _doc(
            _paragraph(
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-183"}},
            ),
        )
        wrapper = {"projectKey": "TP", "type": "Epic", "summary": "x", "description": adf}
        report = self.v.validate(adf, "epic", wrapper)
        t9 = next(c for c in report.checks if c.check_id == "T9")
        assert t9.status != CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T10: Explicit Jira Dependency Links (v3.12.2 — G7)
# ═══════════════════════════════════════════════════════════


class TestT10ExplicitJiraLinks:
    def setup_method(self):
        self.v = AdfValidator()

    def test_no_tp_keys_passes(self):
        adf = _doc(_paragraph(_text("plain description")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t10 = next(c for c in report.checks if c.check_id == "T10")
        assert t10.status == CheckStatus.PASS

    def test_plain_text_tp_key_warns(self):
        adf = _doc(_paragraph(_text("reuse from TP-196 helper")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t10 = next(c for c in report.checks if c.check_id == "T10")
        assert t10.status == CheckStatus.WARN
        assert "TP-196" in t10.message

    def test_inline_card_tp_key_passes(self):
        adf = _doc(
            _paragraph(
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-196"}},
            ),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t10 = next(c for c in report.checks if c.check_id == "T10")
        assert t10.status == CheckStatus.PASS

    def test_t10_never_fails(self):
        adf = _doc(_paragraph(_text("TP-1 TP-2 TP-3 TP-4")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t10 = next(c for c in report.checks if c.check_id == "T10")
        assert t10.status != CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T11: Estimate Declaration (v3.12.2 — G8, Task-only)
# ═══════════════════════════════════════════════════════════


class TestT11Estimate:
    def setup_method(self):
        self.v = AdfValidator()

    def test_missing_estimate_warns(self):
        adf = _doc(_heading("Context"), _paragraph(_text("no estimate")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t11 = next(c for c in report.checks if c.check_id == "T11")
        assert t11.status == CheckStatus.WARN

    def test_estimate_section_passes(self):
        adf = _doc(
            _heading("ประมาณการ (Estimate)"),
            _paragraph(_text("3 SP, 1-2 days")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t11 = next(c for c in report.checks if c.check_id == "T11")
        assert t11.status == CheckStatus.PASS

    def test_story_points_mention_passes(self):
        adf = _doc(_paragraph(_text("This slice is 3 Story Points of work")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t11 = next(c for c in report.checks if c.check_id == "T11")
        assert t11.status == CheckStatus.PASS

    def test_t11_only_runs_for_task(self):
        adf = _doc(_paragraph(_text("x")))
        report = self.v.validate(adf, "epic", {"projectKey": "TP", "type": "Epic", "summary": "x"})
        assert all(c.check_id != "T11" for c in report.checks)
        report = self.v.validate(adf, "task", {"projectKey": "TP", "type": "Task", "summary": "x"})
        assert any(c.check_id == "T11" for c in report.checks)


# ═══════════════════════════════════════════════════════════
# T12: Paired-Epic Regression ACs (v3.12.2 — G9)
# ═══════════════════════════════════════════════════════════


class TestT12PairedEpicRegression:
    def setup_method(self):
        self.v = AdfValidator()

    def test_no_paired_key_passes(self):
        adf = _doc(_heading("Acceptance Criteria"), _paragraph(_text("happy path AC")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t12 = next(c for c in report.checks if c.check_id == "T12")
        assert t12.status == CheckStatus.PASS
        assert "N/A" in t12.message

    def test_paired_key_without_ac_mention_warns(self):
        adf = _doc(
            _paragraph(
                _text("Paired with "),
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-183"}},
            ),
            _heading("Acceptance Criteria"),
            _paragraph(_text("AC1 happy path only")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t12 = next(c for c in report.checks if c.check_id == "T12")
        assert t12.status == CheckStatus.WARN
        assert "TP-183" in t12.message

    def test_paired_key_with_ac_mention_passes(self):
        adf = _doc(
            _paragraph(
                _text("Paired with "),
                {"type": "inlineCard", "attrs": {"url": "https://x.atlassian.net/browse/TP-183"}},
            ),
            _heading("Acceptance Criteria"),
            _paragraph(_text("AC3 regression: TP-183 auto-approve does NOT trigger review")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t12 = next(c for c in report.checks if c.check_id == "T12")
        assert t12.status == CheckStatus.PASS

    def test_t12_never_fails(self):
        adf = _doc(
            _paragraph(_text("TP-183 TP-184 TP-185")),
            _heading("Acceptance Criteria"),
            _paragraph(_text("nothing")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t12 = next(c for c in report.checks if c.check_id == "T12")
        assert t12.status != CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T13: Code Reference Format (v3.12.2 — G10)
# ═══════════════════════════════════════════════════════════


class TestT13CodeReferenceFormat:
    def setup_method(self):
        self.v = AdfValidator()

    def test_bare_method_warns(self):
        adf = _doc(_paragraph(_text("Call "), _text("handle()", marks=[{"type": "code"}])))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t13 = next(c for c in report.checks if c.check_id == "T13")
        assert t13.status == CheckStatus.WARN
        assert "handle()" in t13.message

    def test_class_method_passes(self):
        adf = _doc(
            _paragraph(
                _text("Call "),
                _text("AiMediaAnalysisJob.handle()", marks=[{"type": "code"}]),
            ),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t13 = next(c for c in report.checks if c.check_id == "T13")
        assert t13.status == CheckStatus.PASS

    def test_full_path_passes(self):
        adf = _doc(
            _paragraph(
                _text("Edit "),
                _text("app/Jobs/Foo.ts:Foo.handle()", marks=[{"type": "code"}]),
            ),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t13 = next(c for c in report.checks if c.check_id == "T13")
        assert t13.status == CheckStatus.PASS

    def test_no_code_marks_passes(self):
        adf = _doc(_paragraph(_text("plain text handle() in prose")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t13 = next(c for c in report.checks if c.check_id == "T13")
        assert t13.status == CheckStatus.PASS

    def test_t13_never_fails(self):
        adf = _doc(
            _paragraph(
                _text("run()", marks=[{"type": "code"}]),
                _text("handle()", marks=[{"type": "code"}]),
            ),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t13 = next(c for c in report.checks if c.check_id == "T13")
        assert t13.status != CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T14: Vague AC Phrase Scan (v3.12.2 — G11)
# ═══════════════════════════════════════════════════════════


class TestT14VagueAcPhrases:
    def setup_method(self):
        self.v = AdfValidator()

    def test_no_ac_section_passes_na(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t14 = next(c for c in report.checks if c.check_id == "T14")
        assert t14.status == CheckStatus.PASS

    def test_testable_ac_passes(self):
        adf = _doc(
            _heading("Acceptance Criteria"),
            _paragraph(_text("Given 3 owners, When AI starts, Then all 3 get notification in 5s")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t14 = next(c for c in report.checks if c.check_id == "T14")
        assert t14.status == CheckStatus.PASS

    def test_vague_phrase_english_warns(self):
        adf = _doc(
            _heading("Acceptance Criteria"),
            _paragraph(_text("System should work correctly in all cases")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t14 = next(c for c in report.checks if c.check_id == "T14")
        assert t14.status == CheckStatus.WARN

    def test_vague_phrase_thai_warns(self):
        adf = _doc(
            _heading("Acceptance Criteria"),
            _paragraph(_text("ระบบต้องทำงานได้ดีในทุก scenario")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t14 = next(c for c in report.checks if c.check_id == "T14")
        assert t14.status == CheckStatus.WARN

    def test_t14_never_fails(self):
        adf = _doc(
            _heading("Acceptance Criteria"),
            _paragraph(_text("should work handles properly user-friendly ทำงานได้ดี as expected")),
        )
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "x", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t14 = next(c for c in report.checks if c.check_id == "T14")
        assert t14.status != CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T15: Out of Scope Required for Slices (v3.12.2 — G12, Task-only)
# ═══════════════════════════════════════════════════════════


class TestT15OutOfScopeForSlice:
    def setup_method(self):
        self.v = AdfValidator()

    def test_non_slice_title_passes_na(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {"projectKey": "TP", "type": "Task", "summary": "Add CSV export endpoint", "description": adf}
        report = self.v.validate(adf, "task", wrapper)
        t15 = next(c for c in report.checks if c.check_id == "T15")
        assert t15.status == CheckStatus.PASS
        assert "N/A" in t15.message

    def test_slice_title_without_oos_warns(self):
        adf = _doc(_heading("Context"), _paragraph(_text("no oos")))
        wrapper = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Slice A — single owner notification",
            "description": adf,
        }
        report = self.v.validate(adf, "task", wrapper)
        t15 = next(c for c in report.checks if c.check_id == "T15")
        assert t15.status == CheckStatus.WARN

    def test_vs_label_without_oos_warns(self):
        adf = _doc(_heading("Context"), _paragraph(_text("no oos")))
        wrapper = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "vs1-skeleton — first slice",
            "description": adf,
        }
        report = self.v.validate(adf, "task", wrapper)
        t15 = next(c for c in report.checks if c.check_id == "T15")
        assert t15.status == CheckStatus.WARN

    def test_slice_with_thai_oos_passes(self):
        adf = _doc(
            _heading("ไม่รวมงานนี้ (Out of Scope)"),
            _paragraph(_text("Belongs to TP-200")),
        )
        wrapper = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Slice B — multi-owner",
            "description": adf,
        }
        report = self.v.validate(adf, "task", wrapper)
        t15 = next(c for c in report.checks if c.check_id == "T15")
        assert t15.status == CheckStatus.PASS

    def test_slice_with_english_oos_passes(self):
        adf = _doc(
            _heading("Out of Scope"),
            _paragraph(_text("Belongs to TP-200")),
        )
        wrapper = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Slice B — multi-owner",
            "description": adf,
        }
        report = self.v.validate(adf, "task", wrapper)
        t15 = next(c for c in report.checks if c.check_id == "T15")
        assert t15.status == CheckStatus.PASS

    def test_t15_only_runs_for_task(self):
        adf = _doc(_paragraph(_text("x")))
        report = self.v.validate(adf, "epic", {"projectKey": "TP", "type": "Epic", "summary": "Slice A"})
        assert all(c.check_id != "T15" for c in report.checks)
        report = self.v.validate(adf, "task", {"projectKey": "TP", "type": "Task", "summary": "Slice A"})
        assert any(c.check_id == "T15" for c in report.checks)

    def test_t15_never_fails(self):
        adf = _doc(_paragraph(_text("x")))
        wrapper = {
            "projectKey": "TP",
            "type": "Task",
            "summary": "Slice A — no oos section at all",
            "description": adf,
        }
        report = self.v.validate(adf, "task", wrapper)
        t15 = next(c for c in report.checks if c.check_id == "T15")
        assert t15.status != CheckStatus.FAIL
