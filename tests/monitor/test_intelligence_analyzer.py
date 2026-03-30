"""Tests for monitor/handlers/intelligence_analyzer.py."""
import json
import sys
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from monitor.handlers import intelligence_analyzer as ia  # type: ignore[import-untyped]


def _now_iso(delta_days: float = 0.0) -> str:
    return (datetime.now(UTC) + timedelta(days=delta_days)).isoformat()


def _make_snapshot(keys_statuses: dict) -> dict:
    """Build minimal snapshot: {key: {status, sprint_end_date, status_since, issuetype, sp, parent}}."""
    snap = {}
    for key, status in keys_statuses.items():
        snap[key] = {
            "summary": f"Issue {key}",
            "status": status,
            "assignee": "",
            "priority": "Medium",
            "sprint_end_date": None,
            "status_since": _now_iso(-1),
            "issuetype": "Story",
            "sp": 3,
            "parent": None,
        }
    return snap


_DEFAULT_THRESHOLDS = {
    "velocity_drop_sigma": 2.0,
    "carry_over_spike_pct": 0.40,
    "stagnant_days_default": 7,
    "stagnant_days_override": {},
    "sp_mismatch_pct": 1.5,
    "sp_mismatch_grace_hours": 4,
}

_DEFAULT_CALIBRATION = {
    "schema_version": 1,
    "signal_thresholds": _DEFAULT_THRESHOLDS,
    "service_tags": {},
    "team_carry_over_baseline": 0.20,
}

_BOARD_CONFIG = {
    "columns": {
        "Backlog":        {"wip_max": None, "statuses": ["Backlog", "To Do"]},
        "In Progress":    {"wip_max": 3,    "statuses": ["In Progress"]},
        "In QA":          {"wip_max": 2,    "statuses": ["In QA"]},
        "Done":           {"wip_max": None, "statuses": ["Done"]},
    }
}


def test_detect_wip_breach_fires_when_column_over_limit():
    snapshot = _make_snapshot({
        "TP-1": "In Progress", "TP-2": "In Progress",
        "TP-3": "In Progress", "TP-4": "In Progress",  # 4 > max 3
    })
    # tracking state: wip_breach already tracked for 2 cycles
    tracking = {"In Progress": {"count": 2, "last_seen": _now_iso()}}
    signals = ia._detect_wip_breach(snapshot, _BOARD_CONFIG, tracking, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "wip_breach" for s in signals)


def test_detect_wip_breach_does_not_fire_before_3_consecutive_cycles():
    snapshot = _make_snapshot({
        "TP-1": "In Progress", "TP-2": "In Progress",
        "TP-3": "In Progress", "TP-4": "In Progress",
    })
    # Only 1 cycle tracked so far
    tracking = {"In Progress": {"count": 1, "last_seen": _now_iso()}}
    signals = ia._detect_wip_breach(snapshot, _BOARD_CONFIG, tracking, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "wip_breach" for s in signals)


def test_detect_wip_breach_no_signal_when_within_limit():
    snapshot = _make_snapshot({
        "TP-1": "In Progress", "TP-2": "In Progress",  # 2 <= max 3
    })
    tracking = {"In Progress": {"count": 5, "last_seen": _now_iso()}}
    signals = ia._detect_wip_breach(snapshot, _BOARD_CONFIG, tracking, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "wip_breach" for s in signals)


def test_detect_stagnant_issues_fires_when_status_since_too_old():
    snap = _make_snapshot({"TP-1": "In Progress"})
    snap["TP-1"]["status_since"] = _now_iso(-8)  # 8 days ago, threshold=7
    signals = ia._detect_stagnant_issues(snap, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "stagnant_issue" and s["affected_keys"] == ["TP-1"]
               for s in signals)


def test_detect_stagnant_issues_no_signal_within_threshold():
    snap = _make_snapshot({"TP-1": "In Progress"})
    snap["TP-1"]["status_since"] = _now_iso(-5)  # 5 days ago < threshold=7
    signals = ia._detect_stagnant_issues(snap, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "stagnant_issue" for s in signals)


def test_detect_stagnant_issues_uses_per_tag_override():
    thresholds = {**_DEFAULT_THRESHOLDS, "stagnant_days_override": {"[FE-Web]": 3}}
    snap = _make_snapshot({"TP-1": "In Progress"})
    snap["TP-1"]["status_since"] = _now_iso(-4)  # 4 > 3 (override)
    snap["TP-1"]["service_tag"] = "[FE-Web]"
    signals = ia._detect_stagnant_issues(snap, thresholds)
    assert any(s["signal"] == "stagnant_issue" for s in signals)


def test_detect_stagnant_issues_not_triggered_for_non_in_progress():
    snap = _make_snapshot({"TP-1": "In QA"})
    snap["TP-1"]["status_since"] = _now_iso(-10)
    signals = ia._detect_stagnant_issues(snap, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "stagnant_issue" for s in signals)


def test_detect_carry_over_spike_fires_above_threshold(tmp_path):
    outcomes_path = tmp_path / "story-outcomes.jsonl"
    sprint_id = "42"
    # 3 carry_over, 2 completed in sprint 42 → rate=0.6 > threshold=0.4
    records = [
        {"sprint_id": sprint_id, "outcome": "carry_over", "service_tag": "BE",
         "issue_key": f"TP-{i}", "ts": _now_iso(-2)} for i in range(3)
    ] + [
        {"sprint_id": sprint_id, "outcome": "completed", "service_tag": "BE",
         "issue_key": f"TP-{i+10}", "ts": _now_iso(-2)} for i in range(2)
    ]
    outcomes_path.write_text("\n".join(json.dumps(r) for r in records))
    signals = ia._detect_carry_over_spike(outcomes_path, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "carry_over_spike" for s in signals)


def test_detect_carry_over_spike_no_signal_below_threshold(tmp_path):
    outcomes_path = tmp_path / "story-outcomes.jsonl"
    sprint_id = "42"
    # 1 carry_over, 4 completed → rate=0.2 < threshold=0.4
    records = [
        {"sprint_id": sprint_id, "outcome": "carry_over", "service_tag": "BE",
         "issue_key": "TP-1", "ts": _now_iso(-2)},
    ] + [
        {"sprint_id": sprint_id, "outcome": "completed", "service_tag": "BE",
         "issue_key": f"TP-{i+2}", "ts": _now_iso(-2)} for i in range(4)
    ]
    outcomes_path.write_text("\n".join(json.dumps(r) for r in records))
    signals = ia._detect_carry_over_spike(outcomes_path, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "carry_over_spike" for s in signals)


def test_detect_carry_over_spike_requires_min_5_items(tmp_path):
    outcomes_path = tmp_path / "story-outcomes.jsonl"
    # Only 4 items, 3 carry_over → rate=0.75 but below guard (< 5 items)
    records = [
        {"sprint_id": "42", "outcome": "carry_over", "service_tag": "BE",
         "issue_key": f"TP-{i}", "ts": _now_iso(-2)} for i in range(3)
    ] + [
        {"sprint_id": "42", "outcome": "completed", "service_tag": "BE",
         "issue_key": "TP-99", "ts": _now_iso(-2)}
    ]
    outcomes_path.write_text("\n".join(json.dumps(r) for r in records))
    signals = ia._detect_carry_over_spike(outcomes_path, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "carry_over_spike" for s in signals)


def test_detect_sp_mismatch_fires_when_subtasks_exceed_parent():
    # Parent TP-10: sp=3, In Progress since 5h ago (> grace 4h)
    # Subtasks: TP-11 sp=2, TP-12 sp=3 → sum=5 > 1.5*3=4.5
    snap = {
        "TP-10": {
            "summary": "Parent story", "status": "In Progress",
            "issuetype": "Story", "sp": 3, "parent": None,
            "status_since": _now_iso(-5 / 24),  # 5 hours ago
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
        "TP-11": {
            "summary": "Subtask 1", "status": "In Progress",
            "issuetype": "Sub-task", "sp": 2, "parent": "TP-10",
            "status_since": _now_iso(-1),
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
        "TP-12": {
            "summary": "Subtask 2", "status": "To Do",
            "issuetype": "Sub-task", "sp": 3, "parent": "TP-10",
            "status_since": _now_iso(-1),
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
    }
    signals = ia._detect_sp_mismatch(snap, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "sp_mismatch" and "TP-10" in s["affected_keys"]
               for s in signals)


def test_detect_sp_mismatch_no_signal_within_grace_period():
    # Parent transitioned to In Progress 2 hours ago (< grace 4h) → skip
    snap = {
        "TP-10": {
            "summary": "Parent", "status": "In Progress",
            "issuetype": "Story", "sp": 3, "parent": None,
            "status_since": _now_iso(-2 / 24),  # 2 hours ago
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
        "TP-11": {
            "summary": "Sub", "status": "To Do",
            "issuetype": "Sub-task", "sp": 10, "parent": "TP-10",
            "status_since": _now_iso(-1),
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
    }
    signals = ia._detect_sp_mismatch(snap, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "sp_mismatch" for s in signals)


def test_evict_removes_expired_signals():
    now = datetime.now(UTC)
    signals = [
        {
            "signal": "stagnant_issue", "severity": "warning",
            "generated_at": (now - timedelta(hours=25)).isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),  # expired
            "affected_keys": ["TP-1"],
        },
        {
            "signal": "wip_breach", "severity": "warning",
            "generated_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=23)).isoformat(),  # active
            "affected_keys": [],
        },
    ]
    result = ia._evict(signals)
    assert len(result) == 1
    assert result[0]["signal"] == "wip_breach"


def test_evict_caps_at_10_signals():
    now = datetime.now(UTC)
    signals = [
        {
            "signal": "stagnant_issue", "severity": "warning",
            "generated_at": (now - timedelta(hours=i)).isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "affected_keys": [f"TP-{i}"],
        }
        for i in range(15)
    ]
    result = ia._evict(signals)
    assert len(result) == 10


def test_analyze_writes_insights_json(tmp_path):
    outcomes = tmp_path / "story-outcomes.jsonl"
    insights = tmp_path / "insights.json"
    outcomes.write_text("")  # empty
    snap = _make_snapshot({"TP-1": "In Progress"})
    snap["TP-1"]["status_since"] = _now_iso(-8)

    ia.analyze(
        diff=[],
        new_snapshot=snap,
        old_snapshot={},
        calibration=_DEFAULT_CALIBRATION,
        board_config=_BOARD_CONFIG,
        velocity=None,
        outcomes_path=outcomes,
        insights_path=insights,
    )
    assert insights.exists()
    data = json.loads(insights.read_text())
    assert isinstance(data.get("signals"), list)


def test_analyze_stop_event_prevents_write(tmp_path):
    outcomes = tmp_path / "story-outcomes.jsonl"
    insights = tmp_path / "insights.json"
    outcomes.write_text("")
    stop = threading.Event()
    stop.set()  # already stopped

    ia.analyze(
        diff=[], new_snapshot={}, old_snapshot={},
        calibration=_DEFAULT_CALIBRATION,
        board_config=_BOARD_CONFIG, velocity=None,
        outcomes_path=outcomes, insights_path=insights,
        stop_event=stop,
    )
    assert not insights.exists()
