"""Tests for pre_dor_check.py — DoR gate hook."""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import pre_dor_check


def _run(tool_input: dict, confirmed: str = "") -> dict | None:
    """Run main() with given input. Returns {} on allow, None on block (SystemExit)."""
    data = {"tool_input": tool_input, "session_id": "test"}
    buf = io.StringIO()
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch.dict(os.environ, {"CLAUDE_DOR_CONFIRMED": confirmed}, clear=False),
        redirect_stdout(buf),
    ):
        try:
            pre_dor_check.main()
            return json.loads(buf.getvalue()) if buf.getvalue().strip() else {}
        except SystemExit:
            return None  # blocked


def test_allows_done_transition():
    assert _run({"issue_key": "BEP-1", "transition": "Done"}) is not None


def test_allows_empty_transition():
    assert _run({"issue_key": "BEP-1", "transition": ""}) is not None


def test_allows_review_transition():
    assert _run({"issue_key": "BEP-1", "transition": "In Review"}) is not None


def test_blocks_in_progress_without_confirmation():
    assert _run({"issue_key": "BEP-1", "transition": "In Progress"}) is None


def test_blocks_start_transition():
    assert _run({"issue_key": "BEP-1", "transition": "Start"}) is None


def test_allows_in_progress_with_correct_confirmation():
    assert _run({"issue_key": "BEP-1", "transition": "In Progress"}, confirmed="BEP-1") is not None


def test_blocks_in_progress_with_wrong_confirmation():
    assert _run({"issue_key": "BEP-1", "transition": "In Progress"}, confirmed="BEP-2") is None


def test_confirmation_is_case_insensitive():
    assert _run({"issue_key": "BEP-1", "transition": "in progress"}, confirmed="bep-1") is not None


def test_allows_on_empty_input():
    assert _run({}) is not None
