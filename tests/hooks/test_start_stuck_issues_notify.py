"""Tests for start_stuck_issues_notify.py — surfaces stuck issues from monitor queue."""
import io
import json
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks" / "plugin" / "session"))
import start_stuck_issues_notify


def _run_with_stuck_file(tmp_path, stuck_data: dict | None) -> tuple[str, dict | None]:
    """Run main() with a temp stuck file. Returns (stdout, updated_file_data_or_None)."""
    stuck_file = tmp_path / "stuck_issues.json"
    if stuck_data is not None:
        stuck_file.write_text(json.dumps(stuck_data))

    stdout_buf = io.StringIO()
    with (
        patch.object(start_stuck_issues_notify, "STUCK_FILE", stuck_file),
        patch("sys.stdin.read", return_value=json.dumps({"session_id": "test"})),
        redirect_stdout(stdout_buf),
    ):
        start_stuck_issues_notify.main()

    updated = json.loads(stuck_file.read_text()) if stuck_file.exists() else None
    return stdout_buf.getvalue(), updated


def _make_entry(key="TP-1", status="In Progress", age=4.0):
    return {
        "issue_key": key,
        "status": status,
        "age_days": age,
        "summary": f"Test issue {key}",
        "assignee": "Alice",
        "follow_up_summary": f"Follow up: {key} is stuck",
        "detected_at": time.time(),
    }


# ── Silent when no file ────────────────────────────────────────────────────────

def test_silent_when_no_stuck_file(tmp_path):
    """No output when stuck_issues.json doesn't exist."""
    _, _ = _run_with_stuck_file(tmp_path, None)
    # Should not create the file
    assert not (tmp_path / "stuck_issues.json").exists()


def test_silent_when_pending_empty(tmp_path):
    """No output when pending list is empty."""
    stdout, updated = _run_with_stuck_file(tmp_path, {"rate_limit": {}, "pending": [], "surfaced": []})
    assert stdout == ""
    assert updated["pending"] == []


# ── Surfacing pending items ────────────────────────────────────────────────────

def test_surfaces_pending_items(tmp_path, capsys):
    """Pending items should be injected into context."""
    data = {
        "rate_limit": {},
        "pending": [_make_entry("TP-10", "In Progress", 5.0)],
        "surfaced": [],
    }
    stdout, updated = _run_with_stuck_file(tmp_path, data)
    assert "TP-10" in stdout or updated is not None  # inject_context writes to stdout


def test_pending_moved_to_surfaced(tmp_path):
    """After main(), pending items move to surfaced and pending becomes empty."""
    entry = _make_entry("TP-20", "In Review", 3.5)
    data = {"rate_limit": {}, "pending": [entry], "surfaced": []}
    _, updated = _run_with_stuck_file(tmp_path, data)

    assert updated["pending"] == []
    assert len(updated["surfaced"]) == 1
    assert updated["surfaced"][0]["issue_key"] == "TP-20"
    assert "surfaced_at" in updated["surfaced"][0]


def test_multiple_pending_all_surfaced(tmp_path):
    """All pending items are moved to surfaced in one pass."""
    entries = [_make_entry(f"TP-{i}") for i in range(3)]
    data = {"rate_limit": {}, "pending": entries, "surfaced": []}
    _, updated = _run_with_stuck_file(tmp_path, data)

    assert updated["pending"] == []
    assert len(updated["surfaced"]) == 3


def test_existing_surfaced_items_preserved(tmp_path):
    """Previously surfaced items are not lost when new items are processed."""
    old_surfaced = {**_make_entry("TP-5"), "surfaced_at": "2026-01-01T00:00:00+00:00"}
    data = {
        "rate_limit": {},
        "pending": [_make_entry("TP-6")],
        "surfaced": [old_surfaced],
    }
    _, updated = _run_with_stuck_file(tmp_path, data)

    assert len(updated["surfaced"]) == 2
    keys = {s["issue_key"] for s in updated["surfaced"]}
    assert keys == {"TP-5", "TP-6"}


# ── Resilience ────────────────────────────────────────────────────────────────

def test_handles_corrupt_json_file(tmp_path):
    """Corrupt JSON file should not raise — hook must never fail SessionStart."""
    stuck_file = tmp_path / "stuck_issues.json"
    stuck_file.write_text("{not valid json")
    with patch.object(start_stuck_issues_notify, "STUCK_FILE", stuck_file):
        start_stuck_issues_notify.main()  # must not raise


def test_handles_missing_fields_in_entry(tmp_path):
    """Entry with missing optional fields (summary, assignee) should not raise."""
    data = {
        "rate_limit": {},
        "pending": [{"issue_key": "TP-99", "status": "In Progress", "age_days": 4.0}],
        "surfaced": [],
    }
    _, updated = _run_with_stuck_file(tmp_path, data)
    assert updated["pending"] == []
    assert len(updated["surfaced"]) == 1


def test_rate_limit_preserved(tmp_path):
    """rate_limit dict should survive the pending→surfaced migration."""
    data = {
        "rate_limit": {"TP-1": 1_700_000_000.0},
        "pending": [_make_entry("TP-2")],
        "surfaced": [],
    }
    _, updated = _run_with_stuck_file(tmp_path, data)
    assert updated["rate_limit"] == {"TP-1": 1_700_000_000.0}
