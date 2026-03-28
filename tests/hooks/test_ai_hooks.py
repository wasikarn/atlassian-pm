"""Tests for hook callers: intent_detect, ac_coverage, path_quality."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))


# ── intent_detect ──────────────────────────────────────────────────────────────

from plugin.ai.intent_detect import classify_intent


def _intent_response(intent: str) -> dict:
    return {"intent": intent}


def test_classify_intent_returns_bug():
    with patch("plugin.ai.intent_detect.claude_call_json", return_value=_intent_response("bug")):
        assert classify_intent("สร้าง bug") == "bug"


def test_classify_intent_returns_story():
    with patch("plugin.ai.intent_detect.claude_call_json", return_value=_intent_response("story")):
        assert classify_intent("create a story") == "story"


def test_classify_intent_returns_none_for_none_intent():
    with patch("plugin.ai.intent_detect.claude_call_json", return_value=_intent_response("none")):
        assert classify_intent("what is the status of TP-50") is None


def test_classify_intent_returns_none_when_claude_unavailable():
    with patch("plugin.ai.intent_detect.claude_call_json", return_value=None):
        assert classify_intent("create a bug") is None


def test_classify_intent_lowercases_intent():
    with patch("plugin.ai.intent_detect.claude_call_json", return_value={"intent": "BUG"}):
        assert classify_intent("create bug") == "bug"


def test_classify_intent_returns_none_for_unknown_type():
    with patch("plugin.ai.intent_detect.claude_call_json", return_value={"intent": "unknown_type"}):
        assert classify_intent("do something weird") is None


def test_classify_intent_all_valid_types():
    for intent in ("bug", "story", "epic", "subtask", "task"):
        with patch("plugin.ai.intent_detect.claude_call_json", return_value=_intent_response(intent)):
            assert classify_intent(f"create {intent}") == intent


# ── ac_coverage ────────────────────────────────────────────────────────────────

from plugin.ai.ac_coverage import check_coverage


def test_check_coverage_returns_score():
    with patch("plugin.ai.ac_coverage.claude_call_json", return_value={"score": 85}):
        assert check_coverage(["AC1: login", "AC2: logout"], ["subtask 1", "subtask 2"]) == 85


def test_check_coverage_clamps_to_100():
    with patch("plugin.ai.ac_coverage.claude_call_json", return_value={"score": 150}):
        assert check_coverage(["AC1"], ["s1"]) == 100


def test_check_coverage_clamps_to_0():
    with patch("plugin.ai.ac_coverage.claude_call_json", return_value={"score": -10}):
        assert check_coverage(["AC1"], ["s1"]) == 0


def test_check_coverage_returns_none_when_no_acs():
    assert check_coverage([], ["s1"]) is None


def test_check_coverage_returns_none_when_no_subtasks():
    assert check_coverage(["AC1"], []) is None


def test_check_coverage_returns_none_when_claude_unavailable():
    with patch("plugin.ai.ac_coverage.claude_call_json", return_value=None):
        assert check_coverage(["AC1"], ["s1"]) is None


def test_check_coverage_returns_none_on_non_int_score():
    with patch("plugin.ai.ac_coverage.claude_call_json", return_value={"score": "eighty"}):
        assert check_coverage(["AC1"], ["s1"]) is None


def test_check_coverage_strips_adf_before_scoring():
    """ADF JSON is stripped to plain text before sending to claude."""
    adf_ac = json.dumps({
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC1: user can login"}]}]
    })
    captured = {}

    def fake_call_json(prompt, json_schema, **kwargs):
        captured["prompt"] = prompt
        return {"score": 80}

    with patch("plugin.ai.ac_coverage.claude_call_json", side_effect=fake_call_json):
        score = check_coverage([adf_ac], ["implement login"])

    assert score == 80
    # ADF markup should not appear in the prompt
    assert '{"type":' not in captured["prompt"]
    assert "AC1: user can login" in captured["prompt"]


# ── path_quality ───────────────────────────────────────────────────────────────

from plugin.ai.path_quality import extract_paths, rate_paths, rate_paths_with_suggestion


def test_extract_paths_finds_quoted_files():
    text = 'Found `src/auth/login.py` and "lib/utils.ts" in the codebase'
    paths = extract_paths(text)
    assert "src/auth/login.py" in paths
    assert "lib/utils.ts" in paths


def test_rate_paths_returns_good():
    with patch("plugin.ai.path_quality.claude_call_json", return_value={"rating": "good"}):
        assert rate_paths(["src/foo.ts", "app/bar.py"]) == "good"


def test_rate_paths_returns_fair():
    with patch("plugin.ai.path_quality.claude_call_json", return_value={"rating": "fair"}):
        assert rate_paths(["src/foo.ts", "src/"]) == "fair"


def test_rate_paths_returns_poor():
    with patch("plugin.ai.path_quality.claude_call_json", return_value={"rating": "poor"}):
        assert rate_paths(["src/", "lib/", "app/"]) == "poor"


def test_rate_paths_returns_none_on_empty():
    assert rate_paths([]) is None


def test_rate_paths_returns_none_when_claude_unavailable():
    with patch("plugin.ai.path_quality.claude_call_json", return_value=None):
        assert rate_paths(["src/foo.ts"]) is None


def test_rate_paths_lowercases_rating():
    with patch("plugin.ai.path_quality.claude_call_json", return_value={"rating": "GOOD"}):
        assert rate_paths(["src/foo.ts"]) == "good"


def test_rate_paths_returns_none_for_unknown_rating():
    with patch("plugin.ai.path_quality.claude_call_json", return_value={"rating": "excellent"}):
        assert rate_paths(["src/foo.ts"]) is None


def test_rate_paths_poor_includes_suggestion():
    """When rating is poor, rate_paths_with_suggestion returns the suggestion."""
    response = {"rating": "poor", "suggestion": "Explore src/controllers/ instead of src/"}
    with patch("plugin.ai.path_quality.claude_call_json", return_value=response):
        rating, suggestion = rate_paths_with_suggestion(["src/", "lib/"])
    assert rating == "poor"
    assert suggestion == "Explore src/controllers/ instead of src/"


def test_rate_paths_good_no_suggestion_required():
    """When rating is good, suggestion is None (not required)."""
    response = {"rating": "good"}
    with patch("plugin.ai.path_quality.claude_call_json", return_value=response):
        rating, suggestion = rate_paths_with_suggestion(["src/auth/login.py"])
    assert rating == "good"
    assert suggestion is None


def test_rate_paths_with_suggestion_returns_none_none_on_empty():
    rating, suggestion = rate_paths_with_suggestion([])
    assert rating is None
    assert suggestion is None


def test_rate_paths_with_suggestion_returns_none_none_when_unavailable():
    with patch("plugin.ai.path_quality.claude_call_json", return_value=None):
        rating, suggestion = rate_paths_with_suggestion(["src/"])
    assert rating is None
    assert suggestion is None
