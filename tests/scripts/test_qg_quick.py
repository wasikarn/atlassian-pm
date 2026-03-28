"""Tests for scripts/ai/qg_quick.py — structural_check, content_check, run_quick_check."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai"))
from qg_quick import content_check, run_quick_check, structural_check


# ── fixtures ───────────────────────────────────────────────────────────────────

def _adf(panels=None, ac_lines=None, background_words=30):
    """Build minimal valid ADF with configurable panels, AC lines, background text."""
    bg_text = " ".join(["word"] * background_words)
    content = [
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Background"}],
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": bg_text}],
        },
    ]

    acs = ac_lines or ["AC1: user can login", "AC2: user can logout", "AC3: session expires"]
    for ac in acs:
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": ac}],
        })

    for panel in (panels or []):
        content.append(panel)

    return {"type": "doc", "version": 1, "content": content}


def _panel(with_type: bool = True) -> dict:
    attrs = {"panelType": "info"} if with_type else {}
    return {
        "type": "panel",
        "attrs": attrs,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "note"}]}],
    }


# ── structural_check ──────────────────────────────────────────────────────────

def test_structural_check_valid_adf_has_no_issues():
    issues, ac_count, penalty = structural_check(_adf())
    assert issues == []
    assert ac_count == 3
    assert penalty == 0


def test_structural_check_detects_missing_panel_type():
    adf = _adf(panels=[_panel(with_type=False)])
    issues, _, penalty = structural_check(adf)
    assert any("panelType" in i for i in issues)
    assert penalty >= 15


def test_structural_check_valid_panel_has_no_issue():
    adf = _adf(panels=[_panel(with_type=True)])
    issues, _, _ = structural_check(adf)
    assert not any("panelType" in i for i in issues)


def test_structural_check_detects_low_ac_count():
    adf = _adf(ac_lines=["AC1: only one"])
    issues, ac_count, penalty = structural_check(adf)
    assert any("AC" in i for i in issues)
    assert ac_count == 1
    assert penalty >= 20


def test_structural_check_detects_missing_background():
    adf = _adf(background_words=3)
    issues, _, penalty = structural_check(adf)
    assert any("Background" in i or "background" in i for i in issues)
    assert penalty >= 15


def test_structural_check_invalid_adf_root():
    issues, _, penalty = structural_check({"type": "invalid"})
    assert issues
    assert penalty >= 30


# ── content_check ─────────────────────────────────────────────────────────────

def test_content_check_returns_no_issues_when_all_ok():
    response = {"ac_ok": True, "language_ok": True, "background_ok": True,
                "ac_issues": [], "language_issues": []}
    with patch("qg_quick.run_claude_json", return_value=response):
        issues, penalty, ai_checked = content_check(_adf(), "story")
    assert issues == []
    assert penalty == 0
    assert ai_checked is True


def test_content_check_returns_ac_issues():
    response = {
        "ac_ok": False, "language_ok": True, "background_ok": True,
        "ac_issues": ["AC2 is too vague"], "language_issues": [],
    }
    with patch("qg_quick.run_claude_json", return_value=response):
        issues, penalty, ai_checked = content_check(_adf(), "story")
    assert "AC2 is too vague" in issues
    assert penalty == 10
    assert ai_checked is True


def test_content_check_returns_language_issues():
    response = {
        "ac_ok": True, "language_ok": False, "background_ok": True,
        "ac_issues": [], "language_issues": ["mixed Thai and English"],
    }
    with patch("qg_quick.run_claude_json", return_value=response):
        issues, penalty, ai_checked = content_check(_adf(), "story")
    assert "mixed Thai and English" in issues
    assert penalty == 5
    assert ai_checked is True


def test_content_check_ai_unavailable_is_non_blocking():
    with patch("qg_quick.run_claude_json", return_value=None):
        issues, penalty, ai_checked = content_check(_adf(), "story")
    assert issues == []
    assert penalty == 0
    assert ai_checked is False


def test_content_check_empty_adf_text_is_non_blocking():
    empty_adf = {"type": "doc", "version": 1, "content": []}
    issues, penalty, ai_checked = content_check(empty_adf, "story")
    assert ai_checked is False


# ── run_quick_check ───────────────────────────────────────────────────────────

def test_run_quick_check_skip_full_agent_when_score_high():
    ai_ok = {"ac_ok": True, "language_ok": True, "background_ok": True,
              "ac_issues": [], "language_issues": []}
    with patch("qg_quick.run_claude_json", return_value=ai_ok):
        result = run_quick_check(_adf(), "story")
    assert result["skip_full_agent"] is True
    assert result["score_estimate"] == 100
    assert result["quick_pass"] is True


def test_run_quick_check_does_not_skip_when_ai_unavailable():
    with patch("qg_quick.run_claude_json", return_value=None):
        result = run_quick_check(_adf(), "story")
    assert result["skip_full_agent"] is False
    assert result["ai_checked"] is False


def test_run_quick_check_does_not_skip_when_structural_issues():
    adf = _adf(panels=[_panel(with_type=False)])
    ai_ok = {"ac_ok": True, "language_ok": True, "background_ok": True,
              "ac_issues": [], "language_issues": []}
    with patch("qg_quick.run_claude_json", return_value=ai_ok):
        result = run_quick_check(adf, "story")
    assert result["skip_full_agent"] is False
    assert result["structural_issues"]


def test_run_quick_check_score_reflects_all_penalties():
    adf = _adf(ac_lines=["AC1: only one"], background_words=3,
                panels=[_panel(with_type=False)])
    with patch("qg_quick.run_claude_json", return_value=None):
        result = run_quick_check(adf, "story")
    assert result["score_estimate"] < 70
    assert result["quick_pass"] is False


def test_run_quick_check_result_shape():
    with patch("qg_quick.run_claude_json", return_value=None):
        result = run_quick_check(_adf(), "story")
    assert "quick_pass" in result
    assert "structural_issues" in result
    assert "content_issues" in result
    assert "ac_count" in result
    assert "score_estimate" in result
    assert "skip_full_agent" in result
    assert "ai_checked" in result
