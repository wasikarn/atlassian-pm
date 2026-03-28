#!/usr/bin/env python3
"""Tests for monitor/handlers/stuck_issue_detector.py"""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT))

from monitor.handlers.stuck_issue_detector import (
    _DAY_SECS,
    _RATE_LIMIT_DAYS,
    check_stuck_issues,
    enrich_snapshot_with_status_since,
)
from monitor.state import MonitorState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_state(snapshot: dict) -> MonitorState:
    """Return a MonitorState backed by a temp file pre-populated with snapshot."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = Path(f.name)
    ms = MonitorState(state_path)
    ms.save_snapshot(snapshot)
    return ms


def _make_stuck_state(issue_key: str, status: str, age_days: float) -> MonitorState:
    """Return a MonitorState where issue_key has been in status for age_days."""
    since = time.time() - age_days * _DAY_SECS
    return _make_state({
        issue_key: {
            "summary": "Test issue",
            "status": status,
            "assignee": "alice",
            "_status_since": since,
        }
    })


def _make_snapshot(issue_key: str, status: str, age_days: float) -> dict:
    """Return a minimal snapshot for use as the 'new' snapshot in check_stuck_issues."""
    return {
        issue_key: {
            "summary": "Test issue",
            "status": status,
            "assignee": "alice",
            "_status_since": time.time() - age_days * _DAY_SECS,
        }
    }


class TestCheckStuckIssues(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.stuck_file = Path(self._tmp.name) / "stuck_issues.json"

    def tearDown(self):
        self._tmp.cleanup()

    # ── Threshold detection ───────────────────────────────────────────────────

    def test_in_progress_4_days_is_stuck(self):
        """Issue in 'In Progress' for 4 days → detected (threshold 3)."""
        state = _make_stuck_state("TP-1", "In Progress", age_days=4.0)
        snapshot = _make_snapshot("TP-1", "In Progress", age_days=4.0)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertIn("TP-1", result)

    def test_in_progress_1_day_not_stuck(self):
        """Issue in 'In Progress' for 1 day → NOT detected (threshold 3)."""
        state = _make_stuck_state("TP-1", "In Progress", age_days=1.0)
        snapshot = _make_snapshot("TP-1", "In Progress", age_days=1.0)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertNotIn("TP-1", result)

    def test_in_progress_just_under_3_days_not_stuck(self):
        """2.99 days is under the 3-day threshold → NOT detected."""
        state = _make_stuck_state("TP-1", "In Progress", age_days=2.99)
        snapshot = _make_snapshot("TP-1", "In Progress", age_days=2.99)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertNotIn("TP-1", result)

    def test_in_review_3_days_is_stuck(self):
        """Issue in 'In Review' for 3 days → detected (threshold 2)."""
        state = _make_stuck_state("TP-2", "In Review", age_days=3.0)
        snapshot = _make_snapshot("TP-2", "In Review", age_days=3.0)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertIn("TP-2", result)

    def test_in_review_1_day_not_stuck(self):
        """Issue in 'In Review' for 1 day → NOT detected."""
        state = _make_stuck_state("TP-2", "In Review", age_days=1.0)
        snapshot = _make_snapshot("TP-2", "In Review", age_days=1.0)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertNotIn("TP-2", result)

    def test_done_status_ignored(self):
        """Issues in 'Done' are never flagged."""
        state = _make_stuck_state("TP-3", "Done", age_days=30.0)
        snapshot = _make_snapshot("TP-3", "Done", age_days=30.0)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertNotIn("TP-3", result)

    def test_backlog_status_ignored(self):
        state = _make_stuck_state("TP-4", "Backlog", age_days=30.0)
        snapshot = _make_snapshot("TP-4", "Backlog", age_days=30.0)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertEqual(result, [])

    # ── File output ───────────────────────────────────────────────────────────

    def test_writes_pending_entry_to_file(self):
        state = _make_stuck_state("TP-1", "In Progress", age_days=4.0)
        snapshot = _make_snapshot("TP-1", "In Progress", age_days=4.0)
        check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)

        self.assertTrue(self.stuck_file.exists())
        data = json.loads(self.stuck_file.read_text())
        self.assertEqual(len(data["pending"]), 1)
        entry = data["pending"][0]
        self.assertEqual(entry["issue_key"], "TP-1")
        self.assertEqual(entry["status"], "In Progress")
        self.assertIn("follow_up_summary", entry)

    def test_follow_up_summary_prefix_for_in_review(self):
        state = _make_stuck_state("TP-2", "In Review", age_days=3.0)
        snapshot = _make_snapshot("TP-2", "In Review", age_days=3.0)
        check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)

        data = json.loads(self.stuck_file.read_text())
        entry = data["pending"][0]
        self.assertTrue(entry["follow_up_summary"].startswith("Review follow-up:"))

    def test_follow_up_summary_prefix_for_in_progress(self):
        state = _make_stuck_state("TP-1", "In Progress", age_days=4.0)
        snapshot = _make_snapshot("TP-1", "In Progress", age_days=4.0)
        check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)

        data = json.loads(self.stuck_file.read_text())
        entry = data["pending"][0]
        self.assertTrue(entry["follow_up_summary"].startswith("Follow up:"))

    # ── Rate limiting ─────────────────────────────────────────────────────────

    def test_rate_limit_prevents_duplicate_within_7_days(self):
        """Same issue should not be flagged twice within RATE_LIMIT_DAYS."""
        state = _make_stuck_state("TP-1", "In Progress", age_days=4.0)
        snapshot = _make_snapshot("TP-1", "In Progress", age_days=4.0)
        jira = MagicMock()

        # First call — should detect
        result1 = check_stuck_issues(snapshot, state, jira, stuck_file=self.stuck_file)
        self.assertIn("TP-1", result1)

        # Second call — should be rate-limited
        result2 = check_stuck_issues(snapshot, state, jira, stuck_file=self.stuck_file)
        self.assertNotIn("TP-1", result2)

        # File should still have only 1 pending entry
        data = json.loads(self.stuck_file.read_text())
        self.assertEqual(len(data["pending"]), 1)

    def test_rate_limit_resets_after_7_days(self):
        """After RATE_LIMIT_DAYS, the same issue should be flagged again."""
        state = _make_stuck_state("TP-1", "In Progress", age_days=4.0)
        snapshot = _make_snapshot("TP-1", "In Progress", age_days=4.0)
        jira = MagicMock()

        # Pre-populate rate_limit with an old timestamp
        old_ts = time.time() - (_RATE_LIMIT_DAYS + 1) * _DAY_SECS
        stuck_data = {"rate_limit": {"TP-1": old_ts}, "pending": []}
        self.stuck_file.parent.mkdir(parents=True, exist_ok=True)
        self.stuck_file.write_text(json.dumps(stuck_data))

        result = check_stuck_issues(snapshot, state, jira, stuck_file=self.stuck_file)
        self.assertIn("TP-1", result)

    # ── Multiple issues ───────────────────────────────────────────────────────

    def test_multiple_stuck_issues_all_detected(self):
        now = time.time()
        snapshot = {
            "TP-1": {"summary": "Issue 1", "status": "In Progress", "assignee": "a",
                     "_status_since": now - 4 * _DAY_SECS},
            "TP-2": {"summary": "Issue 2", "status": "In Review", "assignee": "b",
                     "_status_since": now - 3 * _DAY_SECS},
            "TP-3": {"summary": "Issue 3", "status": "To Do", "assignee": "c",
                     "_status_since": now - 10 * _DAY_SECS},
        }
        state = _make_state(snapshot)
        result = check_stuck_issues(snapshot, state, MagicMock(), stuck_file=self.stuck_file)
        self.assertIn("TP-1", result)
        self.assertIn("TP-2", result)
        self.assertNotIn("TP-3", result)  # "To Do" not in thresholds


class TestEnrichSnapshotWithStatusSince(unittest.TestCase):

    def test_new_issue_gets_now_as_since(self):
        before = time.time()
        snapshot = {"TP-1": {"status": "In Progress", "summary": "X", "assignee": ""}}
        empty_state = _make_state({})
        enriched = enrich_snapshot_with_status_since(snapshot, empty_state)
        after = time.time()
        since = enriched["TP-1"]["_status_since"]
        self.assertGreaterEqual(since, before)
        self.assertLessEqual(since, after)

    def test_unchanged_status_preserves_since(self):
        original_since = time.time() - 5 * _DAY_SECS
        old_snapshot = {"TP-1": {"status": "In Progress", "summary": "X",
                                  "assignee": "", "_status_since": original_since}}
        state = _make_state(old_snapshot)
        new_snapshot = {"TP-1": {"status": "In Progress", "summary": "X", "assignee": ""}}
        enriched = enrich_snapshot_with_status_since(new_snapshot, state)
        self.assertAlmostEqual(enriched["TP-1"]["_status_since"], original_since, delta=1.0)

    def test_status_change_resets_since(self):
        original_since = time.time() - 5 * _DAY_SECS
        old_snapshot = {"TP-1": {"status": "To Do", "summary": "X",
                                  "assignee": "", "_status_since": original_since}}
        state = _make_state(old_snapshot)
        new_snapshot = {"TP-1": {"status": "In Progress", "summary": "X", "assignee": ""}}
        before = time.time()
        enriched = enrich_snapshot_with_status_since(new_snapshot, state)
        after = time.time()
        since = enriched["TP-1"]["_status_since"]
        self.assertGreaterEqual(since, before)
        self.assertLessEqual(since, after)

    def test_does_not_mutate_original_snapshot(self):
        snapshot = {"TP-1": {"status": "In Progress", "summary": "X", "assignee": ""}}
        state = _make_state({})
        enrich_snapshot_with_status_since(snapshot, state)
        self.assertNotIn("_status_since", snapshot["TP-1"])


if __name__ == "__main__":
    unittest.main()
