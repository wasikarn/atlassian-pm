#!/usr/bin/env python3
"""Tests for monitor/handlers/velocity_feed.py"""

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure monitor and scripts packages are importable
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT))

from monitor.handlers.velocity_feed import (
    _rolling_average,
    _std_dev,
    _trend_pct,
    update_velocity_from_sprint,
)


class TestRollingAverage(unittest.TestCase):
    def test_empty_list_returns_none(self):
        self.assertIsNone(_rolling_average([], 5))

    def test_fewer_than_window(self):
        result = _rolling_average([10.0, 20.0], 5)
        self.assertAlmostEqual(result, 15.0)

    def test_full_window(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertAlmostEqual(_rolling_average(values, 5), 30.0)

    def test_more_than_window_uses_last_n(self):
        # Last 5 of [1,2,3,4,5,6,7] = [3,4,5,6,7] → avg 5
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        self.assertAlmostEqual(_rolling_average(values, 5), 5.0)


class TestStdDev(unittest.TestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(_std_dev([], 5))

    def test_single_value_returns_none(self):
        self.assertIsNone(_std_dev([10.0], 5))

    def test_uniform_values_zero_std(self):
        self.assertAlmostEqual(_std_dev([5.0, 5.0, 5.0], 5), 0.0)

    def test_known_std_dev(self):
        # Sample std dev of [2, 4, 4, 4, 5, 5, 7, 9]:
        # mean=5, sum_sq_diff=32, variance=32/7≈4.571, std≈2.138
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        result = _std_dev(values, 8)
        self.assertAlmostEqual(result, 2.138089935299395, places=5)

    def test_uses_last_window_values(self):
        # Only last 3 values should be considered: [10, 10, 10] → std = 0
        values = [1.0, 2.0, 3.0, 10.0, 10.0, 10.0]
        self.assertAlmostEqual(_std_dev(values, 3), 0.0)


class TestTrendPct(unittest.TestCase):
    def test_fewer_than_2window_returns_none(self):
        self.assertIsNone(_trend_pct([10.0, 20.0], window=3))

    def test_flat_trend_is_zero(self):
        values = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        result = _trend_pct(values, window=3)
        self.assertAlmostEqual(result, 0.0)

    def test_upward_trend(self):
        # prev avg = (5+10+15)/3 = 10, last avg = (20+25+30)/3 = 25 → +150%
        values = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
        result = _trend_pct(values, window=3)
        self.assertAlmostEqual(result, 150.0)

    def test_downward_trend(self):
        # prev avg = 30, last avg = 15 → -50%
        values = [30.0, 30.0, 30.0, 15.0, 15.0, 15.0]
        result = _trend_pct(values, window=3)
        self.assertAlmostEqual(result, -50.0)

    def test_zero_prev_avg_returns_none(self):
        values = [0.0, 0.0, 0.0, 10.0, 10.0, 10.0]
        self.assertIsNone(_trend_pct(values, window=3))


class TestUpdateVelocityFromSprint(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)
        self.config_path = self.tmp_dir / "project-config-team-detail.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _load_config(self):
        return json.loads(self.config_path.read_text())

    # ── Basic write ──────────────────────────────────────────────────────────

    def test_creates_file_when_absent(self):
        result = update_velocity_from_sprint(
            {"sprint_id": 1, "completed_sp": 20.0, "total_sp": 25.0, "date": "2026-01-14"},
            config_path=self.config_path,
        )
        self.assertTrue(result)
        self.assertTrue(self.config_path.exists())

    def test_appends_sprint_to_history(self):
        update_velocity_from_sprint(
            {"sprint_id": 1, "completed_sp": 20.0, "total_sp": 25.0, "date": "2026-01-14"},
            config_path=self.config_path,
        )
        config = self._load_config()
        history = config["velocity"]["sprint_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["sprint_id"], 1)
        self.assertAlmostEqual(history[0]["completed_sp"], 20.0)

    def test_skips_duplicate_sprint(self):
        sprint = {"sprint_id": 1, "completed_sp": 20.0, "total_sp": 25.0, "date": "2026-01-14"}
        update_velocity_from_sprint(sprint, config_path=self.config_path)
        result = update_velocity_from_sprint(sprint, config_path=self.config_path)
        self.assertFalse(result)
        config = self._load_config()
        self.assertEqual(len(config["velocity"]["sprint_history"]), 1)

    def test_missing_sprint_id_returns_false(self):
        result = update_velocity_from_sprint(
            {"completed_sp": 20.0, "date": "2026-01-14"},
            config_path=self.config_path,
        )
        self.assertFalse(result)

    # ── Rolling average ──────────────────────────────────────────────────────

    def test_rolling_average_calculated_from_last_5(self):
        sprints = [
            {"sprint_id": i, "completed_sp": float(i * 10), "date": f"2026-0{i}-01"}
            for i in range(1, 8)  # 7 sprints: 10,20,30,40,50,60,70
        ]
        for s in sprints:
            update_velocity_from_sprint(s, config_path=self.config_path)

        config = self._load_config()
        # Last 5 sprints: 30,40,50,60,70 → avg 50
        self.assertAlmostEqual(config["velocity"]["rolling_average"], 50.0)

    # ── Trend ────────────────────────────────────────────────────────────────

    def test_trend_pct_calculated_with_6_sprints(self):
        # prev 3 avg: 10 → last 3 avg: 40 → trend = +300%
        for i, sp in enumerate([10.0, 10.0, 10.0, 40.0, 40.0, 40.0], start=1):
            update_velocity_from_sprint(
                {"sprint_id": i, "completed_sp": sp, "date": f"2026-0{i}-01"},
                config_path=self.config_path,
            )
        config = self._load_config()
        self.assertAlmostEqual(config["velocity"]["trend_pct"], 300.0)

    def test_trend_pct_none_with_insufficient_data(self):
        for i in range(1, 6):  # only 5 sprints — need 6 for trend_pct with window=3
            update_velocity_from_sprint(
                {"sprint_id": i, "completed_sp": float(i * 10), "date": f"2026-0{i}-01"},
                config_path=self.config_path,
            )
        config = self._load_config()
        self.assertIsNone(config["velocity"]["trend_pct"])

    # ── Metadata ─────────────────────────────────────────────────────────────

    def test_last_updated_sprint_reflects_latest(self):
        for i in range(1, 4):
            update_velocity_from_sprint(
                {"sprint_id": i, "completed_sp": 20.0, "date": f"2026-0{i}-01"},
                config_path=self.config_path,
            )
        config = self._load_config()
        self.assertEqual(config["velocity"]["last_updated_sprint"], 3)

    def test_sprints_tracked_increments(self):
        for i in range(1, 4):
            update_velocity_from_sprint(
                {"sprint_id": i, "completed_sp": 20.0, "date": f"2026-0{i}-01"},
                config_path=self.config_path,
            )
        config = self._load_config()
        self.assertEqual(config["velocity"]["sprints_tracked"], 3)

    # ── Preserves existing keys ───────────────────────────────────────────────

    def test_preserves_existing_config_keys(self):
        # Write a pre-existing config with unrelated data
        initial = {"git_evidence": {"Tech Lead": "10 commits"}, "velocity": {}}
        self.config_path.write_text(json.dumps(initial))

        update_velocity_from_sprint(
            {"sprint_id": 1, "completed_sp": 20.0, "date": "2026-01-14"},
            config_path=self.config_path,
        )
        config = self._load_config()
        self.assertIn("git_evidence", config)
        self.assertEqual(config["git_evidence"]["Tech Lead"], "10 commits")


if __name__ == "__main__":
    unittest.main()
