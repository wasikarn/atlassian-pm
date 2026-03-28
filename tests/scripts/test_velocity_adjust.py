"""Tests for scripts/ai/velocity_adjust.py — load_velocity, compute_adjustment, format_context."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai"))
from velocity_adjust import compute_adjustment, format_context, load_velocity


# ── load_velocity ──────────────────────────────────────────────────────────────

def test_load_velocity_returns_none_when_no_config(tmp_path):
    result = load_velocity(tmp_path / "nonexistent.json")
    assert result is None


def test_load_velocity_returns_none_when_no_config_in_tree(tmp_path):
    # tmp_path has no .claude/ dir — auto-discovery should return None
    # We can't easily test cwd-walk without monkeypatching, so pass explicit missing path
    result = load_velocity(tmp_path / "project-config-team-detail.json")
    assert result is None


def test_load_velocity_returns_velocity_section(tmp_path):
    config = {
        "velocity": {
            "rolling_average": 40,
            "trend_pct": -8,
            "std_dev": 5,
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    result = load_velocity(config_file)
    assert result == config["velocity"]


def test_load_velocity_returns_none_when_velocity_key_missing(tmp_path):
    config = {"git_evidence": {}}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    result = load_velocity(config_file)
    assert result is None


def test_load_velocity_returns_none_on_invalid_json(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text("{ not valid json }")
    result = load_velocity(config_file)
    assert result is None


# ── compute_adjustment ─────────────────────────────────────────────────────────

def test_compute_adjustment_declining_trend_applies_negative_adjustment():
    velocity = {"rolling_average": 40, "trend_pct": -8, "std_dev": 4}
    adj = compute_adjustment(velocity)
    assert adj["adjustment_pct"] < 0
    assert adj["note"] != ""
    assert "declining" in adj["note"]


def test_compute_adjustment_declining_trend_caps_at_minus_15():
    # trend_pct = -40 → 40 * 0.5 = -20, but capped at -15
    velocity = {"rolling_average": 50, "trend_pct": -40, "std_dev": 5}
    adj = compute_adjustment(velocity)
    assert adj["adjustment_pct"] == -15


def test_compute_adjustment_improving_trend_no_negative_adjustment():
    velocity = {"rolling_average": 45, "trend_pct": 10, "std_dev": 3}
    adj = compute_adjustment(velocity)
    assert adj["adjustment_pct"] == 0
    assert "improving" in adj["note"]


def test_compute_adjustment_flat_trend_no_adjustment():
    velocity = {"rolling_average": 38, "trend_pct": 2, "std_dev": 3}
    adj = compute_adjustment(velocity)
    assert adj["adjustment_pct"] == 0
    assert adj["note"] == ""


def test_compute_adjustment_high_std_dev_sets_high_variance():
    # std_dev=10 > 40 * 0.2=8 → high_variance
    velocity = {"rolling_average": 40, "trend_pct": 0, "std_dev": 10}
    adj = compute_adjustment(velocity)
    assert adj["high_variance"] is True


def test_compute_adjustment_low_std_dev_not_high_variance():
    # std_dev=5 < 40 * 0.2=8 → not high_variance
    velocity = {"rolling_average": 40, "trend_pct": 0, "std_dev": 5}
    adj = compute_adjustment(velocity)
    assert adj["high_variance"] is False


def test_compute_adjustment_reads_nested_story_points_schema():
    # velocity-tracker writes to story_points.avg_velocity
    velocity = {
        "story_points": {"avg_velocity": 42, "std_dev": 6},
        "trend_pct": -8,
    }
    adj = compute_adjustment(velocity)
    assert adj["rolling_average"] == 42
    assert adj["std_dev"] == 6
    assert adj["adjustment_pct"] < 0


def test_compute_adjustment_zero_avg_does_not_flag_high_variance():
    velocity = {"rolling_average": 0, "trend_pct": 0, "std_dev": 5}
    adj = compute_adjustment(velocity)
    assert adj["high_variance"] is False


# ── format_context ─────────────────────────────────────────────────────────────

def test_format_context_contains_velocity_context_prefix():
    adj = {
        "rolling_average": 42,
        "trend_pct": -8,
        "std_dev": 6.0,
        "adjustment_pct": -4,
        "note": "team velocity declining 8%",
        "high_variance": False,
    }
    output = format_context(adj)
    assert output.startswith("Velocity Context:")


def test_format_context_negative_adjustment_includes_velocity_adjustment_line():
    adj = {
        "rolling_average": 42,
        "trend_pct": -8,
        "std_dev": 6.0,
        "adjustment_pct": -4,
        "note": "team velocity declining 8%",
        "high_variance": False,
    }
    output = format_context(adj)
    assert "Velocity Adjustment:" in output
    assert "-4%" in output


def test_format_context_improving_trend_shows_velocity_note_not_adjustment():
    adj = {
        "rolling_average": 48,
        "trend_pct": 9,
        "std_dev": 3.5,
        "adjustment_pct": 0,
        "note": "team velocity improving 9%",
        "high_variance": False,
    }
    output = format_context(adj)
    assert "Velocity Note:" in output
    assert "Velocity Adjustment:" not in output


def test_format_context_high_variance_includes_warning():
    adj = {
        "rolling_average": 38,
        "trend_pct": 1,
        "std_dev": 10.2,
        "adjustment_pct": 0,
        "note": "",
        "high_variance": True,
    }
    output = format_context(adj)
    assert "⚠️" in output


def test_format_context_no_note_no_extra_lines():
    adj = {
        "rolling_average": 40,
        "trend_pct": 0,
        "std_dev": 4.0,
        "adjustment_pct": 0,
        "note": "",
        "high_variance": False,
    }
    output = format_context(adj)
    lines = output.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("Velocity Context:")
