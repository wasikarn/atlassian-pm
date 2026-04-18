"""Tests for scripts/lib/adf_validator.py — AdfValidator, utilities, and data classes."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "lib"))
from adf_validator import (
    AdfValidator,
    CheckResult,
    CheckStatus,
    QG_THRESHOLD,
    VALID_PANEL_TYPES,
    ValidationReport,
    detect_format,
    extract_text,
    find_adf_nodes,
    find_headings,
    get_section_content,
    walk_adf,
)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


def _make_doc(*content_nodes):
    """Build minimal valid ADF doc."""
    return {"type": "doc", "version": 1, "content": list(content_nodes)}


def _make_panel(panel_type="info", *content):
    return {
        "type": "panel",
        "attrs": {"panelType": panel_type},
        "content": list(content) or [_make_paragraph("panel text")],
    }


def _make_paragraph(*texts):
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": t} for t in texts],
    }


def _make_heading(level, text):
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _make_gwt_text():
    return "Given: user is logged in When: user visits dashboard Then: they see their profile"


def _make_ac_panel(panel_type="success"):
    return _make_panel(panel_type, _make_paragraph(_make_gwt_text()))


def _story_doc():
    """Build a passing story ADF document with all required sections."""
    return _make_doc(
        _make_heading(2, "User Story"),
        _make_panel(
            "info",
            _make_paragraph(
                "As a teacher, I want to see my student list, So that I can track attendance easily."
            ),
        ),
        _make_heading(2, "Background"),
        _make_paragraph(
            "ระบบต้องการให้ครูสามารถดูรายชื่อนักเรียนได้อย่างรวดเร็ว เพื่อช่วยในการจัดการชั้นเรียน"
        ),
        _make_heading(2, "Acceptance Criteria"),
        _make_ac_panel("success"),
        _make_heading(2, "Scope"),
        _make_paragraph(
            "ส่วนที่ครอบคลุม: teacher dashboard component, student list API endpoint"
        ),
    )


VALIDATOR = AdfValidator()


# ═══════════════════════════════════════════════════════════
# T1 — ADF Format check
# ═══════════════════════════════════════════════════════════


def test_t1_valid_doc_passes():
    doc = _make_doc(_make_paragraph("hello"))
    result = VALIDATOR._check_t1_adf_format(doc)
    assert result.status == CheckStatus.PASS


def test_t1_invalid_type_fails():
    doc = {"type": "invalid", "version": 1, "content": [_make_paragraph("x")]}
    result = VALIDATOR._check_t1_adf_format(doc)
    assert result.status == CheckStatus.FAIL
    assert "doc" in result.message


def test_t1_wrong_version_fails():
    doc = {"type": "doc", "version": 2, "content": [_make_paragraph("x")]}
    result = VALIDATOR._check_t1_adf_format(doc)
    assert result.status == CheckStatus.FAIL


def test_t1_empty_content_fails():
    doc = {"type": "doc", "version": 1, "content": []}
    result = VALIDATOR._check_t1_adf_format(doc)
    assert result.status == CheckStatus.FAIL


def test_t1_missing_content_fails():
    doc = {"type": "doc", "version": 1}
    result = VALIDATOR._check_t1_adf_format(doc)
    assert result.status == CheckStatus.FAIL


# ═══════════════════════════════════════════════════════════
# T2 — Panel type checks
# ═══════════════════════════════════════════════════════════


@pytest.mark.parametrize("panel_type", ["info", "success", "warning", "error", "note"])
def test_t2_valid_panel_types_pass(panel_type):
    doc = _make_doc(_make_panel(panel_type))
    result = VALIDATOR._check_t2_panels(doc)
    assert result.status == CheckStatus.PASS


def test_t2_invalid_panel_type_fails():
    doc = _make_doc(_make_panel("highlight"))
    result = VALIDATOR._check_t2_panels(doc)
    assert result.status == CheckStatus.FAIL
    assert "panelType" in result.message or "highlight" in result.message


def test_t2_no_panels_warns():
    doc = _make_doc(_make_paragraph("no panels here"))
    result = VALIDATOR._check_t2_panels(doc)
    assert result.status == CheckStatus.WARN


def test_t2_nested_table_warns():
    table = {"type": "table", "content": []}
    panel = _make_panel("info", table)
    doc = _make_doc(panel)
    result = VALIDATOR._check_t2_panels(doc)
    assert result.status == CheckStatus.WARN


# ═══════════════════════════════════════════════════════════
# T5 — Required fields
# ═══════════════════════════════════════════════════════════


def test_t5_no_wrapper_passes_if_content_present():
    doc = _make_doc(_make_paragraph("content"))
    result = VALIDATOR._check_t5_required_fields(doc, "story", None)
    assert result.status == CheckStatus.PASS


def test_t5_no_wrapper_fails_if_no_content():
    doc = {"type": "doc", "version": 1, "content": []}
    result = VALIDATOR._check_t5_required_fields(doc, "story", None)
    assert result.status == CheckStatus.FAIL


def test_t5_create_wrapper_all_fields_passes():
    doc = _make_doc(_make_paragraph("x"))
    wrapper = {
        "projectKey": "TP",
        "type": "Story",
        "summary": "Test story",
        "description": doc,
    }
    result = VALIDATOR._check_t5_required_fields(doc, "story", wrapper)
    assert result.status == CheckStatus.PASS


def test_t5_create_wrapper_missing_field_fails():
    doc = _make_doc(_make_paragraph("x"))
    wrapper = {"projectKey": "TP", "type": "Story", "description": doc}  # missing summary
    result = VALIDATOR._check_t5_required_fields(doc, "story", wrapper)
    assert result.status == CheckStatus.FAIL
    assert "summary" in result.message


def test_t5_edit_wrapper_with_forbidden_field_fails():
    doc = _make_doc(_make_paragraph("x"))
    wrapper = {"issues": ["TP-1"], "description": doc, "summary": "should not be here"}
    result = VALIDATOR._check_t5_required_fields(doc, "story", wrapper)
    assert result.status == CheckStatus.FAIL
    assert "summary" in result.message


def test_t5_edit_wrapper_valid_passes():
    doc = _make_doc(_make_paragraph("x"))
    wrapper = {"issues": ["TP-1"], "description": doc}
    result = VALIDATOR._check_t5_required_fields(doc, "story", wrapper)
    assert result.status == CheckStatus.PASS


# ═══════════════════════════════════════════════════════════
# S1 — INVEST (Story: small + testable)
# ═══════════════════════════════════════════════════════════


def test_s1_invest_with_gwt_panels_passes():
    secs = {"acceptance criteria": [_make_ac_panel("success")]}
    result = VALIDATOR._check_s1_invest(secs)
    assert result.status == CheckStatus.PASS


def test_s1_invest_no_ac_panels_fails():
    secs = {"acceptance criteria": []}
    result = VALIDATOR._check_s1_invest(secs)
    assert result.status == CheckStatus.FAIL


def test_s1_invest_panels_without_gwt_fails():
    panel = _make_panel("success", _make_paragraph("Do the thing"))
    secs = {"acceptance criteria": [panel]}
    result = VALIDATOR._check_s1_invest(secs)
    assert result.status == CheckStatus.FAIL


def test_s1_invest_too_many_panels_warns():
    panels = [_make_ac_panel("success") for _ in range(6)]
    secs = {"acceptance criteria": panels}
    result = VALIDATOR._check_s1_invest(secs)
    assert result.status == CheckStatus.WARN


# ═══════════════════════════════════════════════════════════
# S2 — Narrative (As a / I want / So that)
# ═══════════════════════════════════════════════════════════


def test_s2_narrative_full_format_passes():
    secs = {
        "user story": [
            _make_paragraph(
                "As a teacher, I want to manage classes, So that I can organize better."
            )
        ]
    }
    result = VALIDATOR._check_s2_narrative(secs, _make_doc(_make_paragraph("dummy")))
    assert result.status == CheckStatus.PASS


def test_s2_narrative_missing_all_parts_fails():
    secs = {"user story": [_make_paragraph("The system should work well.")]}
    result = VALIDATOR._check_s2_narrative(secs, _make_doc(_make_paragraph("dummy")))
    assert result.status == CheckStatus.FAIL


def test_s2_narrative_no_section_falls_back_to_info_panel():
    doc = _make_doc(
        _make_panel(
            "info",
            _make_paragraph(
                "As a manager, I want a report, So that I can track performance."
            ),
        )
    )
    result = VALIDATOR._check_s2_narrative({}, doc)
    assert result.status == CheckStatus.PASS


# ═══════════════════════════════════════════════════════════
# S4 — AC format (Given/When/Then + panel types)
# ═══════════════════════════════════════════════════════════


def test_s4_ac_panels_with_gwt_passes():
    secs = {"acceptance criteria": [_make_ac_panel("success")]}
    result = VALIDATOR._check_s4_acceptance_criteria(secs)
    assert result.status == CheckStatus.PASS


def test_s4_no_ac_panels_fails():
    secs = {"acceptance criteria": []}
    result = VALIDATOR._check_s4_acceptance_criteria(secs)
    assert result.status == CheckStatus.FAIL


def test_s4_panels_without_gwt_warns_or_fails():
    panel = _make_panel("success", _make_paragraph("Just do it"))
    secs = {"acceptance criteria": [panel]}
    result = VALIDATOR._check_s4_acceptance_criteria(secs)
    # zero GWT → FAIL; partial GWT → WARN
    assert result.status in (CheckStatus.FAIL, CheckStatus.WARN)


# ═══════════════════════════════════════════════════════════
# S6 / Language check
# ═══════════════════════════════════════════════════════════


def test_language_check_thai_content_passes():
    doc = _make_doc(_make_paragraph("ระบบนี้ดีมาก"))
    result = VALIDATOR._check_language("S6", doc)
    assert result.status == CheckStatus.PASS


def test_language_check_english_only_fails():
    doc = _make_doc(_make_paragraph("This is a system in English only."))
    result = VALIDATOR._check_language("S6", doc)
    assert result.status == CheckStatus.FAIL


def test_language_check_empty_warns():
    doc = {"type": "doc", "version": 1, "content": []}
    result = VALIDATOR._check_language("S6", doc)
    assert result.status == CheckStatus.WARN


# ═══════════════════════════════════════════════════════════
# ST4 — Subtask tag on summary
# ═══════════════════════════════════════════════════════════


@pytest.mark.parametrize("tag", ["[BE]", "[FE-Admin]", "[FE-Web]", "[QA]"])
def test_st4_valid_tag_on_summary_passes(tag):
    doc = _make_doc(_make_paragraph("content"))
    wrapper = {
        "projectKey": "TP",
        "type": "Sub-task",
        "summary": f"{tag} Implement login endpoint",
        "description": doc,
    }
    result = VALIDATOR._check_st4_tag_summary(doc, wrapper)
    assert result.status == CheckStatus.PASS


def test_st4_missing_tag_on_summary_fails():
    doc = _make_doc(_make_paragraph("content"))
    wrapper = {
        "projectKey": "TP",
        "type": "Sub-task",
        "summary": "Implement login endpoint without tag",
        "description": doc,
    }
    result = VALIDATOR._check_st4_tag_summary(doc, wrapper)
    assert result.status == CheckStatus.FAIL


def test_st4_no_wrapper_warns():
    doc = _make_doc(_make_paragraph("content"))
    result = VALIDATOR._check_st4_tag_summary(doc, None)
    assert result.status == CheckStatus.WARN


# ═══════════════════════════════════════════════════════════
# E2 — RICE score
# ═══════════════════════════════════════════════════════════


def test_e2_rice_section_absent_passes_optional():
    # RICE is optional per template
    secs = {}
    result = VALIDATOR._check_e2_rice(secs)
    assert result.status == CheckStatus.PASS


def test_e2_rice_with_all_factors_passes():
    table = {"type": "table", "content": []}
    rice_section = [
        table,
        _make_paragraph("Reach: 1000 Impact: high Confidence: 80% Effort: 3"),
    ]
    secs = {"rice": rice_section}
    result = VALIDATOR._check_e2_rice(secs)
    assert result.status == CheckStatus.PASS


def test_e2_rice_missing_factors_warns():
    table = {"type": "table", "content": []}
    rice_section = [table, _make_paragraph("Reach: 1000")]
    secs = {"rice": rice_section}
    result = VALIDATOR._check_e2_rice(secs)
    assert result.status == CheckStatus.WARN


# ═══════════════════════════════════════════════════════════
# ValidationReport scoring
# ═══════════════════════════════════════════════════════════


def test_validation_report_score_all_pass():
    report = ValidationReport(issue_type="story")
    report.checks = [
        CheckResult("T1", CheckStatus.PASS, "ok"),
        CheckResult("T2", CheckStatus.PASS, "ok"),
    ]
    assert report.score == 100.0
    assert report.passed is True


def test_validation_report_score_all_fail():
    report = ValidationReport(issue_type="story")
    report.checks = [
        CheckResult("T1", CheckStatus.FAIL, "fail"),
        CheckResult("T2", CheckStatus.FAIL, "fail"),
    ]
    assert report.score == 0.0
    assert report.passed is False


def test_validation_report_score_warn_is_half():
    report = ValidationReport(issue_type="story")
    report.checks = [CheckResult("T1", CheckStatus.WARN, "warn")]
    assert report.score == 50.0


def test_validation_report_empty_checks_score_zero():
    report = ValidationReport(issue_type="story")
    assert report.score == 0.0


def test_validation_report_to_dict_shape():
    report = ValidationReport(issue_type="story")
    report.checks = [
        CheckResult("T1", CheckStatus.PASS, "ok"),
        CheckResult("T2", CheckStatus.FAIL, "bad", fix_hint="fix it"),
    ]
    d = report.to_dict()
    assert d["issue_type"] == "story"
    assert "score" in d
    assert "status" in d
    assert "total_checks" in d
    assert d["total_checks"] == 2
    assert d["failed"] == 1
    assert len(d["issues"]) == 1
    assert d["issues"][0]["fix_hint"] == "fix it"


def test_validation_report_qg_threshold_is_90():
    assert QG_THRESHOLD == 90.0


# ═══════════════════════════════════════════════════════════
# ADF Utility functions
# ═══════════════════════════════════════════════════════════


def test_extract_text_from_nested_doc():
    doc = _make_doc(
        _make_panel("info", _make_paragraph("hello", "world"))
    )
    text = extract_text(doc)
    assert "hello" in text
    assert "world" in text


def test_extract_text_empty_doc_returns_empty():
    doc = {"type": "doc", "version": 1, "content": []}
    text = extract_text(doc)
    assert text == ""


def test_walk_adf_visits_all_nodes():
    visited = []
    doc = _make_doc(_make_panel("info", _make_paragraph("x")))
    walk_adf(doc, lambda n: visited.append(n.get("type")))
    assert "doc" in visited
    assert "panel" in visited
    assert "paragraph" in visited
    assert "text" in visited


def test_find_adf_nodes_returns_matching():
    doc = _make_doc(_make_panel("info"), _make_panel("warning"))
    panels = find_adf_nodes(doc, lambda n: n.get("type") == "panel")
    assert len(panels) == 2


def test_find_headings_by_level():
    doc = _make_doc(
        _make_heading(2, "Background"),
        _make_heading(2, "Acceptance Criteria"),
        _make_heading(3, "Sub-heading"),
    )
    h2 = find_headings(doc, level=2)
    assert len(h2) == 2
    h3 = find_headings(doc, level=3)
    assert len(h3) == 1


def test_get_section_content_returns_nodes_after_heading():
    doc = _make_doc(
        _make_heading(2, "Background"),
        _make_paragraph("background content"),
        _make_heading(2, "Acceptance Criteria"),
        _make_paragraph("ac content"),
    )
    section = get_section_content(doc, "background")
    assert len(section) == 1
    assert extract_text(section) == "background content"


# ═══════════════════════════════════════════════════════════
# detect_format
# ═══════════════════════════════════════════════════════════


def test_detect_format_raw_adf():
    doc = _make_doc(_make_paragraph("x"))
    fmt, extracted = detect_format(doc)
    assert fmt == "raw"
    assert extracted is doc


def test_detect_format_create_wrapper():
    doc = _make_doc(_make_paragraph("x"))
    wrapper = {"projectKey": "TP", "type": "Story", "description": doc}
    fmt, extracted = detect_format(wrapper)
    assert fmt == "create"
    assert extracted is doc


def test_detect_format_edit_wrapper():
    doc = _make_doc(_make_paragraph("x"))
    wrapper = {"issues": ["TP-1"], "description": doc}
    fmt, extracted = detect_format(wrapper)
    assert fmt == "edit"
    assert extracted is doc


# ═══════════════════════════════════════════════════════════
# Auto-fix methods
# ═══════════════════════════════════════════════════════════


def test_fix_panel_types_replaces_invalid_with_info():
    doc = _make_doc(_make_panel("highlight"))
    fixed_count = VALIDATOR._fix_panel_types(doc)
    assert fixed_count == 1
    panel = find_adf_nodes(doc, lambda n: n.get("type") == "panel")[0]
    assert panel["attrs"]["panelType"] == "info"


def test_fix_panel_types_leaves_valid_unchanged():
    doc = _make_doc(_make_panel("warning"))
    fixed_count = VALIDATOR._fix_panel_types(doc)
    assert fixed_count == 0


# ═══════════════════════════════════════════════════════════
# S7 — Markdown-in-text scan
# ═══════════════════════════════════════════════════════════


def test_s7_para_break_in_text_node_warns_by_default():
    doc = _make_doc(_make_paragraph("line one\n\nline two"))
    result = AdfValidator()._check_s7_markdown_in_text(doc)
    assert result.status == CheckStatus.WARN
    assert "para-break" in result.message


def test_s7_para_break_in_text_node_fails_when_markdown_strict_true():
    doc = _make_doc(_make_paragraph("line one\n\nline two"))
    result = AdfValidator(markdown_strict=True)._check_s7_markdown_in_text(doc)
    assert result.status == CheckStatus.FAIL
    assert "para-break" in result.message


def test_s7_pipe_table_row_detected():
    doc = _make_doc(_make_paragraph("| col1 | col2 |"))
    result = AdfValidator()._check_s7_markdown_in_text(doc)
    assert result.status == CheckStatus.WARN
    assert "pipe-table row" in result.message


def test_s7_bullet_prefix_detected():
    doc = _make_doc(_make_paragraph("- item one\n- item two"))
    result = AdfValidator()._check_s7_markdown_in_text(doc)
    assert result.status == CheckStatus.WARN
    assert "bullet prefix" in result.message


def test_s7_markdown_heading_detected():
    doc = _make_doc(_make_paragraph("## My Heading"))
    result = AdfValidator()._check_s7_markdown_in_text(doc)
    assert result.status == CheckStatus.WARN
    assert "markdown heading" in result.message


def test_s7_code_marked_text_is_exempt():
    text_node = {"type": "text", "text": "## heading inside code", "marks": [{"type": "code"}]}
    doc = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [text_node]}]}
    result = AdfValidator()._check_s7_markdown_in_text(doc)
    assert result.status == CheckStatus.PASS


def test_s7_deeply_nested_text_node_detected():
    # bullet prefix inside panel > blockquote > paragraph > text
    inner_text = {"type": "text", "text": "- nested bullet item"}
    inner_para = {"type": "paragraph", "content": [inner_text]}
    blockquote = {"type": "blockquote", "content": [inner_para]}
    panel = _make_panel("info", blockquote)
    doc = _make_doc(panel)
    result = AdfValidator()._check_s7_markdown_in_text(doc)
    assert result.status == CheckStatus.WARN
    assert "bullet prefix" in result.message


# ═══════════════════════════════════════════════════════════
# S8 — Dual-zone AC check
# ═══════════════════════════════════════════════════════════


def _make_dual_zone_ac_doc(biz_h3: bool = True, dev_h3: bool = True) -> dict:
    """Build an ADF doc with AC H2 section and optional Business/Developer H3 zones."""
    ac_content: list[dict] = []
    if biz_h3:
        ac_content.append(_make_heading(3, "Acceptance Criteria — Business"))
        ac_content.append(_make_paragraph("ผู้ใช้เห็น dashboard ของตัวเองทันทีหลังล็อกอิน"))
    if dev_h3:
        ac_content.append(_make_heading(3, "Acceptance Criteria — Developer"))
        ac_content.append(
            _make_paragraph(
                "Given: user is logged in When: user visits dashboard Then: 200 OK"
            )
        )
    return _make_doc(
        _make_heading(2, "Acceptance Criteria"),
        *ac_content,
    )


def test_s8_story_missing_both_zones_warns_by_default():
    # AC H2 present but no H3 zones at all
    doc = _make_doc(
        _make_heading(2, "Acceptance Criteria"),
        _make_paragraph("some criteria"),
    )
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.WARN
    assert "Business AC zone" in result.message or "Developer AC zone" in result.message


def test_s8_story_missing_both_zones_fails_when_strict():
    doc = _make_doc(
        _make_heading(2, "Acceptance Criteria"),
        _make_paragraph("some criteria"),
    )
    result = AdfValidator(dual_zone_strict=True)._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.FAIL


def test_s8_story_missing_developer_zone_warns():
    doc = _make_dual_zone_ac_doc(biz_h3=True, dev_h3=False)
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.WARN
    assert "Developer AC zone" in result.message


def test_s8_story_with_both_zones_passes():
    doc = _make_dual_zone_ac_doc(biz_h3=True, dev_h3=True)
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.PASS


def test_s8_task_only_requires_developer_zone():
    # Task: developer required, business optional — developer zone alone should pass
    doc = _make_dual_zone_ac_doc(biz_h3=False, dev_h3=True)
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "task")
    assert result.status == CheckStatus.PASS


def test_s8_subtask_business_zone_skipped():
    # Subtask: business=skip, developer=required — developer zone alone passes
    doc = _make_dual_zone_ac_doc(biz_h3=False, dev_h3=True)
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "subtask")
    assert result.status == CheckStatus.PASS


def test_s8_qa_type_both_zones_optional():
    # QA: both optional — no zones needed, passes regardless
    doc = _make_doc(_make_paragraph("no AC structure needed for QA"))
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "qa")
    assert result.status == CheckStatus.PASS


def test_s8_business_zone_language_leak_sla_warns():
    doc = _make_doc(
        _make_heading(2, "Acceptance Criteria"),
        _make_heading(3, "Acceptance Criteria — Business"),
        _make_paragraph("Response time must be under 30s for all users"),
        _make_heading(3, "Acceptance Criteria — Developer"),
        _make_paragraph("Given: request sent When: processed Then: 200 OK"),
    )
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.WARN
    assert "SLA" in result.message or "30s" in result.message or "jargon" in result.message


def test_s8_business_zone_language_leak_service_warns():
    doc = _make_doc(
        _make_heading(2, "Acceptance Criteria"),
        _make_heading(3, "Acceptance Criteria — Business"),
        _make_paragraph("Notification is sent via Pusher to the connected client"),
        _make_heading(3, "Acceptance Criteria — Developer"),
        _make_paragraph("Given: event triggered When: pushed Then: client receives"),
    )
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.WARN
    assert "service" in result.message.lower() or "jargon" in result.message.lower()


def test_s8_business_zone_language_leak_method_call_warns():
    doc = _make_doc(
        _make_heading(2, "Acceptance Criteria"),
        _make_heading(3, "Acceptance Criteria — Business"),
        _make_paragraph("System calls AuthService.login() to authenticate the user"),
        _make_heading(3, "Acceptance Criteria — Developer"),
        _make_paragraph("Given: credentials valid When: login called Then: token returned"),
    )
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.WARN
    assert "method" in result.message.lower() or "jargon" in result.message.lower()


def test_s8_no_ac_section_warns_when_required():
    # Story with no AC H2 at all → warn (grandfather mode)
    doc = _make_doc(
        _make_heading(2, "User Story"),
        _make_paragraph("As a user I want to login"),
    )
    result = AdfValidator()._check_s8_dual_zone_ac(doc, "story")
    assert result.status == CheckStatus.WARN
    assert "AC section" in result.message or "No AC" in result.message


def test_auto_fix_returns_new_report():
    doc = _make_doc(_make_panel("highlight"))
    report = VALIDATOR.validate(doc, "task")
    fixed_doc, new_report = VALIDATOR.auto_fix(doc, report)
    # fixed doc should have a valid panel
    panel = find_adf_nodes(fixed_doc, lambda n: n.get("type") == "panel")[0]
    assert panel["attrs"]["panelType"] in VALID_PANEL_TYPES


# ═══════════════════════════════════════════════════════════
# Full validate() integration — None / empty input guards
# ═══════════════════════════════════════════════════════════


def test_validate_returns_report_with_checks():
    doc = _story_doc()
    report = VALIDATOR.validate(doc, "story")
    assert isinstance(report, ValidationReport)
    assert len(report.checks) > 0


def test_validate_empty_doc_fails_t1():
    doc = {"type": "doc", "version": 1, "content": []}
    report = VALIDATOR.validate(doc, "task")
    t1 = next(c for c in report.checks if c.check_id == "T1")
    assert t1.status == CheckStatus.FAIL


def test_validate_invalid_issue_type_runs_technical_only():
    # Invalid issue type → only T1–T5 checks, no quality checks
    doc = _make_doc(_make_paragraph("hello"))
    report = VALIDATOR.validate(doc, "unknown_type")
    check_ids = [c.check_id for c in report.checks]
    assert "T1" in check_ids
    # No quality checks for unknown type
    quality_ids = [c for c in check_ids if not c.startswith("T")]
    assert quality_ids == []


def test_validate_deeply_nested_valid_content():
    """Deeply nested structure should not crash the validator."""
    inner = _make_paragraph("deep text")
    for _ in range(5):
        inner = {"type": "blockquote", "content": [inner]}
    doc = _make_doc(inner)
    # Should not raise
    report = VALIDATOR.validate(doc, "task")
    assert report is not None


def test_validate_all_issue_types_return_report():
    doc = _make_doc(_make_paragraph("test content ภาษาไทย"))
    for issue_type in ("story", "subtask", "epic", "qa", "task"):
        report = VALIDATOR.validate(doc, issue_type)
        assert isinstance(report, ValidationReport)
        assert report.issue_type == issue_type
        assert len(report.checks) >= 5  # at least T1-T5


def test_valid_panel_types_constant():
    assert VALID_PANEL_TYPES == frozenset({"info", "success", "warning", "error", "note"})
