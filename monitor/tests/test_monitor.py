#!/usr/bin/env python3
"""Tests for monitor/*.py"""

import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
