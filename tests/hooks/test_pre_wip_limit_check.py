"""Tests for pre_wip_limit_check.py — WIP limit hard-gate hook."""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks" / "plugin" / "guards"))
import pre_wip_limit_check

# Minimal board config matching project-config.json structure
_BOARD_CONFIG = {
    "jira": {"project_key": "TP"},
    "board": {
        "columns": {
            "In Progress": {
                "wip_max": 10,
                "statuses": ["In Progress"],
            },
            "In QA": {
                "wip_max": 4,
                "statuses": ["In QA"],
            },
            "Done": {
                "wip_max": None,
                "statuses": ["Done", "Closed"],
            },
        }
    },
}


def _run(tool_input: dict, confirmed: str = "", config: dict | None = None) -> dict | None:
    """Run main() with given input. Returns {} on allow, None on block (SystemExit)."""
    data = {"tool_input": tool_input, "session_id": "test"}
    buf = io.StringIO()
    cfg = config if config is not None else {}
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch("pre_wip_limit_check._load_config", return_value=cfg),
        patch.dict(os.environ, {"CLAUDE_WIP_CONFIRMED": confirmed}, clear=False),
        redirect_stdout(buf),
    ):
        try:
            pre_wip_limit_check.main()
            raw = buf.getvalue().strip()
            return json.loads(raw) if raw else {}
        except SystemExit:
            return None  # blocked


def test_ignores_done_transition():
    """Done has wip_max=None so no blocking even with config."""
    assert _run({"issue_key": "TP-1", "transition": "Done"}, config=_BOARD_CONFIG) == {}


def test_ignores_in_review_transition():
    """Unknown transition not in any column → allow."""
    assert _run({"issue_key": "TP-1", "transition": "In Review"}, config=_BOARD_CONFIG) == {}


def test_ignores_empty_transition():
    assert _run({"issue_key": "TP-1", "transition": ""}, config=_BOARD_CONFIG) == {}


def test_blocks_in_progress_without_confirmation():
    """In Progress has wip_max=10, no env confirmation → block."""
    result = _run({"issue_key": "TP-1", "transition": "In Progress"}, config=_BOARD_CONFIG)
    assert result is None  # blocked (SystemExit 2)


def test_blocks_in_qa_without_confirmation():
    """In QA has wip_max=4, no confirmation → block."""
    result = _run({"issue_key": "TP-1", "transition": "In QA"}, config=_BOARD_CONFIG)
    assert result is None


def test_allows_in_progress_with_correct_confirmation():
    """Correct CLAUDE_WIP_CONFIRMED=<key>:<col> bypasses the gate."""
    result = _run(
        {"issue_key": "TP-42", "transition": "In Progress"},
        confirmed="TP-42:In Progress",
        config=_BOARD_CONFIG,
    )
    assert result == {}


def test_allows_in_progress_with_wrong_confirmation():
    """Wrong confirmation key → still blocked."""
    result = _run(
        {"issue_key": "TP-42", "transition": "In Progress"},
        confirmed="TP-99:In Progress",
        config=_BOARD_CONFIG,
    )
    assert result is None


def test_allows_when_no_board_config():
    """Without board config the hook allows everything (graceful degradation)."""
    assert _run({"issue_key": "TP-1", "transition": "In Progress"}) == {}


def test_allows_on_empty_input():
    assert _run({}, config=_BOARD_CONFIG) == {}
