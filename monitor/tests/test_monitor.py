#!/usr/bin/env python3
"""Tests for monitor/*.py"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from state import MonitorState, diff_snapshots


class TestMonitorState(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            self.state_path = Path(tmp.name)

    def tearDown(self):
        self.state_path.unlink(missing_ok=True)

    def test_saves_and_loads_snapshot(self):
        ms = MonitorState(self.state_path)
        ms.save_snapshot({"TP-1": {"status": "In Progress", "assignee": "alice"}})
        loaded = ms.load_snapshot()
        self.assertEqual(loaded["TP-1"]["status"], "In Progress")

    def test_returns_empty_dict_if_no_file(self):
        path = Path("/tmp/nonexistent_monitor_state_xyz.json")
        ms = MonitorState(path)
        self.assertEqual(ms.load_snapshot(), {})

    def test_diff_detects_status_change(self):
        old = {"TP-1": {"status": "To Do", "summary": "Feature X"}}
        new = {"TP-1": {"status": "In Progress", "summary": "Feature X"}}
        changes = diff_snapshots(old, new)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["key"], "TP-1")
        self.assertIn("status", changes[0]["changed_fields"])

    def test_diff_detects_new_issue(self):
        old = {}
        new = {"TP-2": {"status": "To Do", "summary": "New issue"}}
        changes = diff_snapshots(old, new)
        self.assertEqual(len(changes), 1)
        self.assertTrue(changes[0]["is_new"])

    def test_diff_ignores_unchanged(self):
        snapshot = {"TP-1": {"status": "Done", "summary": "Done issue"}}
        changes = diff_snapshots(snapshot, snapshot)
        self.assertEqual(changes, [])

    def test_diff_ignores_resolved_issues(self):
        """Issues no longer in new snapshot (moved to Done) produce no change event."""
        old = {"TP-1": {"status": "In Progress"}, "TP-2": {"status": "In Progress"}}
        new = {"TP-2": {"status": "In Progress"}}  # TP-1 resolved and gone
        changes = diff_snapshots(old, new)
        # diff_snapshots only iterates new.items() — removed keys produce no events
        self.assertEqual(len(changes), 0)


class TestIssueChanged(unittest.TestCase):
    def _make_change(self, key="TP-1", summary="Test", status="In Progress", changed_fields=None):
        return {
            "key": key,
            "issue": {"summary": summary, "status": status},
            "changed_fields": changed_fields or {"status": ("To Do", "In Progress")},
        }

    def test_returns_false_when_no_changed_fields(self):
        from handlers.issue_changed import handle
        change = self._make_change(changed_fields={})
        result = handle(change, MagicMock())
        self.assertFalse(result)

    def test_posts_comment_on_note_response(self):
        from handlers.issue_changed import handle
        jira = MagicMock()
        with patch("handlers.issue_changed.run_claude", return_value="NOTE: this is significant"):
            result = handle(self._make_change(), jira)
        self.assertTrue(result)
        jira.add_comment.assert_called_once()

    def test_skips_on_skip_response(self):
        from handlers.issue_changed import handle
        jira = MagicMock()
        with patch("handlers.issue_changed.run_claude", return_value="SKIP"):
            result = handle(self._make_change(), jira)
        self.assertFalse(result)
        jira.add_comment.assert_not_called()

    def test_returns_false_when_claude_unavailable(self):
        from handlers.issue_changed import handle
        jira = MagicMock()
        with patch("handlers.issue_changed.run_claude", return_value=None):
            result = handle(self._make_change(), jira)
        self.assertFalse(result)


class TestSprintHealth(unittest.TestCase):
    def _board_config(self):
        return {
            "columns": {
                "In Progress": {"wip_max": 2, "statuses": ["In Progress"]},
                "Done": {"wip_max": None, "statuses": ["Done"]},
            }
        }

    def test_no_alerts_when_within_limits(self):
        from handlers.sprint_health import handle
        issues = [{"status": "In Progress"}, {"status": "Done"}]
        with patch("handlers.sprint_health._send_imessage") as mock_send:
            alerts = handle(self._board_config(), issues)
        mock_send.assert_not_called()
        self.assertEqual(alerts, [])

    def test_wip_alert_when_exceeded(self):
        from handlers.sprint_health import handle
        issues = [{"status": "In Progress"}, {"status": "In Progress"}, {"status": "In Progress"}]
        with patch("handlers.sprint_health._send_imessage"), \
             patch("handlers.sprint_health._should_alert", return_value=True), \
             patch("handlers.sprint_health._mark_alerted"):
            alerts = handle(self._board_config(), issues)
        self.assertEqual(len(alerts), 1)
        self.assertIn("WIP LIMIT", alerts[0])


if __name__ == "__main__":
    unittest.main()
