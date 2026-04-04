"""Tests for pre_search_before_create.py — dedup block before issue creation."""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks" / "plugin" / "cache"))
import pre_search_before_create


def _run(tool_input: dict, search_done: bool = False) -> dict | None:
    """Run main() with given input. Returns {} on allow (exit 0), None on block (exit 1/2)."""
    data = {"tool_input": tool_input, "session_id": "test-session"}
    buf = io.StringIO()
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch("pre_search_before_create.search_is_done", return_value=search_done),
        redirect_stdout(buf),
    ):
        try:
            pre_search_before_create.main()
            raw = buf.getvalue().strip()
            return json.loads(raw) if raw else {}
        except SystemExit as e:
            # Exit code 0 = allow, exit code 1 or 2 = block
            if e.code == 0:
                return {}
            return None  # blocked


# ── Search done → always allow ────────────────────────────────────────────


def test_allows_when_search_done_story():
    """Prior search recorded → allow story creation (may inject semantic tip)."""
    result = _run({"issuetype": "Story", "summary": "New feature"}, search_done=True)
    assert result is not None  # not blocked; hook may inject cache_similar_issues tip


def test_allows_when_search_done_task():
    """Prior search recorded → allow task creation (may inject semantic tip)."""
    result = _run({"issuetype": "Task", "summary": "Fix bug"}, search_done=True)
    assert result is not None


def test_allows_when_search_done_empty_input():
    """Prior search recorded → allow even with minimal input."""
    result = _run({}, search_done=True)
    assert result is not None


# ── Subtask exemption → allow even without search ────────────────────────


def test_allows_subtask_without_search():
    """Sub-task is exempt from dedup search requirement."""
    result = _run({"issuetype": "Sub-task"}, search_done=False)
    assert result is not None  # not blocked


def test_allows_subtask_variant_without_search():
    """'subtask' (no hyphen) is also treated as subtask → exempt."""
    result = _run({"issuetype": "subtask"}, search_done=False)
    assert result is not None


def test_allows_sub_task_uppercase():
    """Case-insensitive subtask detection: SUB-TASK → exempt."""
    result = _run({"issuetype": "SUB-TASK"}, search_done=False)
    assert result is not None


# ── No search done + non-subtask → block ─────────────────────────────────


def test_blocks_story_without_search():
    """Story creation without prior search → block."""
    result = _run({"issuetype": "Story", "summary": "Add login"}, search_done=False)
    assert result is None


def test_blocks_task_without_search():
    """Task creation without prior search → block."""
    result = _run({"issuetype": "Task"}, search_done=False)
    assert result is None


def test_blocks_epic_without_search():
    """Epic creation without prior search → block."""
    result = _run({"issuetype": "Epic", "summary": "New epic"}, search_done=False)
    assert result is None


def test_blocks_empty_issuetype_without_search():
    """Unknown/empty issuetype without prior search → block (not exempt)."""
    result = _run({"summary": "Some issue"}, search_done=False)
    assert result is None


# ── Block message content ─────────────────────────────────────────────────


def test_block_message_mentions_dedup():
    """Block reason must mention duplicate prevention."""
    captured_stderr = io.StringIO()
    data = {"tool_input": {"issuetype": "Story"}, "session_id": "test-session"}
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch("pre_search_before_create.search_is_done", return_value=False),
        patch("sys.stderr", captured_stderr),
    ):
        try:
            pre_search_before_create.main()
        except SystemExit:
            pass

    err = captured_stderr.getvalue()
    assert "DEDUP" in err or "duplicate" in err.lower() or "search" in err.lower()


def test_block_message_includes_project_key():
    """Block reason includes a project key hint for the search JQL."""
    captured_stderr = io.StringIO()
    data = {"tool_input": {"issuetype": "Story"}, "session_id": "test-session"}
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch("pre_search_before_create.search_is_done", return_value=False),
        patch("pre_search_before_create._PROJECT_KEY", "TP"),
        patch("sys.stderr", captured_stderr),
    ):
        try:
            pre_search_before_create.main()
        except SystemExit:
            pass

    err = captured_stderr.getvalue()
    assert "TP" in err
