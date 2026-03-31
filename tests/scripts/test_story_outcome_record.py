"""Tests for scripts/story_outcome_record.py — calibrate spawn behavior."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import story_outcome_record  # type: ignore[import-untyped]

_ISSUE = {"key": "TP-1", "summary": "auth fix", "status": "Done", "sp": 3,
          "assignee": None, "issuetype": "Story", "labels": ["be"]}


def _run_main(tmp_path, monkeypatch, issues=None):
    """Helper: patch env, run main() with given issues list."""
    monkeypatch.setattr(story_outcome_record, "DATA_DIR", tmp_path)
    monkeypatch.setattr(story_outcome_record, "STORY_OUTCOMES", tmp_path / "story-outcomes.jsonl")
    monkeypatch.setattr(
        sys, "argv",
        [
            "story_outcome_record.py",
            "--sprint-id", "1",
            "--sprint-name", "S1",
            "--issues-json", json.dumps(issues or [_ISSUE]),
        ],
    )
    story_outcome_record.main()


def test_spawns_calibrate_when_plugin_root_and_script_exist(tmp_path, monkeypatch):
    """Popen is called with calibrate.py path and start_new_session=True."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    calibrate_path = tmp_path / "scripts" / "ai" / "calibrate.py"
    calibrate_path.parent.mkdir(parents=True)
    calibrate_path.touch()

    with patch.object(story_outcome_record.subprocess, "Popen") as mock_popen:
        _run_main(tmp_path, monkeypatch)

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert str(calibrate_path) in args[0]
    assert kwargs["start_new_session"] is True
    assert kwargs["stdout"] == story_outcome_record.subprocess.DEVNULL


def test_does_not_spawn_when_plugin_root_unset(tmp_path, monkeypatch):
    """No Popen call when CLAUDE_PLUGIN_ROOT env var is not set."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

    with patch.object(story_outcome_record.subprocess, "Popen") as mock_popen:
        _run_main(tmp_path, monkeypatch)

    mock_popen.assert_not_called()


def test_does_not_spawn_when_calibrate_missing(tmp_path, monkeypatch):
    """No Popen call when calibrate.py does not exist at expected path."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    # Do NOT create calibrate.py

    with patch.object(story_outcome_record.subprocess, "Popen") as mock_popen:
        _run_main(tmp_path, monkeypatch)

    mock_popen.assert_not_called()
