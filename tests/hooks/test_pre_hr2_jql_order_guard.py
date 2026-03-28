"""Tests for pre_hr2_jql_order_guard.py — HR2 JQL ORDER BY + parent block."""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks" / "plugin" / "guards"))
import pre_hr2_jql_order_guard


def _run(tool_input: dict) -> dict | None:
    """Run main() with given input. Returns {} on allow, None on block (SystemExit)."""
    data = {"tool_input": tool_input, "session_id": "test"}
    buf = io.StringIO()
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        redirect_stdout(buf),
    ):
        try:
            pre_hr2_jql_order_guard.main()
            raw = buf.getvalue().strip()
            return json.loads(raw) if raw else {}
        except SystemExit:
            return None  # blocked


# ── Blocking cases ────────────────────────────────────────────────────────


def test_blocks_parent_eq_with_order_by():
    """parent = <value> combined with ORDER BY must be blocked."""
    result = _run({"jql": "project = TP AND parent = TP-100 ORDER BY created DESC"})
    assert result is None


def test_blocks_parent_in_with_order_by():
    """parent in (...) combined with ORDER BY must be blocked."""
    result = _run({"jql": "parent in (TP-100, TP-101) ORDER BY updated ASC"})
    assert result is None


def test_blocks_case_insensitive_order_by():
    """ORDER BY detection is case-insensitive (lowercase 'order by' still blocked)."""
    result = _run({"jql": "parent = TP-50 order by priority"})
    assert result is None


def test_blocks_case_insensitive_parent():
    """parent keyword detection is case-insensitive."""
    result = _run({"jql": "PARENT = TP-50 ORDER BY created"})
    assert result is None


def test_blocks_query_field_with_parent_and_order_by():
    """Also works when the field key is 'query' instead of 'jql'."""
    result = _run({"query": "parent = TP-10 ORDER BY summary"})
    assert result is None


# ── Allowing cases ────────────────────────────────────────────────────────


def test_allows_order_by_without_parent():
    """ORDER BY alone (no parent clause) is safe — allow."""
    result = _run({"jql": "project = TP AND status = 'In Progress' ORDER BY created DESC"})
    assert result == {}


def test_allows_parent_without_order_by():
    """parent = without ORDER BY is safe — allow."""
    result = _run({"jql": "parent = TP-100 AND status = 'To Do'"})
    assert result == {}


def test_allows_empty_jql():
    """Empty JQL → allow (no clause to check)."""
    result = _run({"jql": ""})
    assert result == {}


def test_allows_missing_jql_field():
    """No jql/query field in tool_input → allow."""
    result = _run({})
    assert result == {}


def test_allows_unrelated_jql():
    """Completely unrelated JQL without parent or ORDER BY → allow."""
    result = _run({"jql": "project = TP AND issuetype = Story"})
    assert result == {}


def test_allows_parent_word_in_summary():
    """The word 'parent' in a text search value should not trigger the guard."""
    # 'summary ~ "parent issue"' does not have 'parent =' or 'parent in' pattern
    result = _run({"jql": "summary ~ 'parent issue' ORDER BY created"})
    assert result == {}


# ── Block message content ─────────────────────────────────────────────────


def test_block_message_mentions_hr2():
    """The block reason must contain 'HR2' for traceability."""
    captured_stderr = io.StringIO()
    data = {
        "tool_input": {"jql": "parent = TP-1 ORDER BY created"},
        "session_id": "test",
    }
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch("sys.stderr", captured_stderr),
    ):
        try:
            pre_hr2_jql_order_guard.main()
        except SystemExit:
            pass

    err = captured_stderr.getvalue()
    assert "HR2" in err
    assert "ORDER BY" in err
