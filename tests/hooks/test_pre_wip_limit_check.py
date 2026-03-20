"""Tests for pre_wip_limit_check.py — WIP limit soft-guard hook."""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import pre_wip_limit_check


def _run(tool_input: dict) -> dict:
    data = {"tool_input": tool_input, "session_id": "test"}
    buf = io.StringIO()
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        redirect_stdout(buf),
    ):
        pre_wip_limit_check.main()
    raw = buf.getvalue().strip()
    return json.loads(raw) if raw else {}


def _has_context(result: dict) -> bool:
    return "additionalContext" in str(result)


def test_ignores_done_transition():
    assert _run({"issue_key": "BEP-1", "transition": "Done"}) == {}


def test_ignores_in_review_transition():
    assert _run({"issue_key": "BEP-1", "transition": "In Review"}) == {}


def test_ignores_empty_transition():
    assert _run({"issue_key": "BEP-1", "transition": ""}) == {}


def test_injects_for_in_progress():
    result = _run({"issue_key": "BEP-1", "transition": "In Progress"})
    assert _has_context(result)


def test_injects_for_start_transition():
    result = _run({"issue_key": "BEP-1", "transition": "Start"})
    assert _has_context(result)


def test_output_contains_wip_check_instruction():
    result = _run({"issue_key": "BEP-42", "transition": "In Progress"})
    context = str(result)
    assert "BEP-42" in context
    assert "In Progress" in context


def test_allows_on_empty_input():
    assert _run({}) == {}
