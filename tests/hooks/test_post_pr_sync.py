"""Tests for post_pr_sync.py — auto-inject Jira transition after gh pr create."""
import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks" / "dev"))
import post_pr_sync

# The module computes _ISSUE_RE at import time from CLAUDE_PLUGIN_ROOT env,
# which is empty in test environments. Patch it to a known pattern for tests.
_TEST_ISSUE_RE = re.compile(r'\b(TP-\d+|TP-\d+)\b', re.IGNORECASE)


def _run(command: str, tool_response: str = "") -> dict:
    data = {
        "tool_input": {"command": command},
        "tool_response": tool_response,
        "session_id": "test",
    }
    buf = io.StringIO()
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch.object(post_pr_sync, "_ISSUE_RE", _TEST_ISSUE_RE),
        redirect_stdout(buf),
    ):
        post_pr_sync.main()
    raw = buf.getvalue().strip()
    return json.loads(raw) if raw else {}


def _has_context(result: dict) -> bool:
    return "additionalContext" in str(result)


def test_ignores_git_push():
    assert _run("git push origin main") == {}


def test_ignores_gh_pr_list():
    assert _run("gh pr list") == {}


def test_ignores_gh_pr_create_with_no_bep():
    assert _run("gh pr create --title 'fix typo' --body ''") == {}


def test_detects_bep_in_title():
    result = _run("gh pr create --title 'TP-123: add feature' --body ''")
    assert _has_context(result)
    assert "TP-123" in str(result)


def test_detects_bep_in_branch_flag():
    result = _run("gh pr create --head TP-456/my-branch --body ''")
    assert "TP-456" in str(result)


def test_detects_bep_in_tool_response():
    result = _run("gh pr create --body ''", tool_response="Created PR for TP-789")
    assert "TP-789" in str(result)


def test_bep_detection_is_case_insensitive():
    result = _run("gh pr create --title 'bep-321 fix' --body ''")
    assert "TP-321" in str(result)


def test_context_includes_transition_instruction():
    result = _run("gh pr create --title 'TP-100: feat' --body ''")
    context = str(result)
    assert "In Review" in context
    assert "cache_invalidate" in context
