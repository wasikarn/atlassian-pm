#!/usr/bin/env python3
"""Proactive board intelligence analyzer — pure Python, zero LLM calls.

Detects 5 signals from board snapshot + outcomes history. All thresholds are
read from calibration.json["signal_thresholds"] at runtime. Writes insights.json
atomically. Called from board_monitor.py in a daemon thread after snapshot save.
"""

import json
import os
import re
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)
_INSIGHTS_FILE = _DATA_DIR / "insights.json"
_OUTCOMES_FILE = _DATA_DIR / "story-outcomes.jsonl"
_MAX_ACTIVE_SIGNALS = 10

_TTL_HOURS = {
    "velocity_drop": 72,
    "carry_over_spike": 72,
    "wip_breach": 24,
    "stagnant_issue": 24,
    "sp_mismatch": 24,
}

_DEFAULT_THRESHOLDS = {
    "velocity_drop_sigma": 2.0,
    "carry_over_spike_pct": 0.40,
    "stagnant_days_default": 7,
    "stagnant_days_override": {},
    "sp_mismatch_pct": 1.5,
    "sp_mismatch_grace_hours": 4,
}


# ── File helpers ──────────────────────────────────────────────────────────────

def _load_insights(path: Path) -> dict:
    """Load insights.json → {signals: [], wip_breach_tracking: {}}."""
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return {"signals": [], "wip_breach_tracking": {}}
        data.setdefault("signals", [])
        data.setdefault("wip_breach_tracking", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"signals": [], "wip_breach_tracking": {}}


def _write_insights(path: Path, data: dict) -> None:
    """Write insights.json atomically with 0o600 permissions."""
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", opener=lambda p, f: os.open(p, f, 0o600)) as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _evict(signals: list[dict]) -> list[dict]:
    """Remove expired entries; cap at _MAX_ACTIVE_SIGNALS (oldest first)."""
    now = datetime.now(UTC)
    active = []
    for s in signals:
        try:
            exp = datetime.fromisoformat(s["expires_at"].replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if exp > now:
                active.append(s)
        except (KeyError, ValueError):
            active.append(s)  # keep if no expiry info
    # If still over cap, evict oldest by generated_at
    if len(active) > _MAX_ACTIVE_SIGNALS:
        active.sort(key=lambda s: s.get("generated_at", ""))
        active = active[-_MAX_ACTIVE_SIGNALS:]
    return active


def _is_dedup(signal_type: str, dedup_key: tuple, existing: list[dict]) -> bool:
    """Return True if a non-expired signal with same dedup_key already exists."""
    now = datetime.now(UTC)
    for s in existing:
        if s.get("signal") != signal_type:
            continue
        exp_str = s.get("expires_at", "")
        try:
            exp = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if exp <= now:
                continue
        except ValueError:
            pass
        if tuple(s.get("_dedup_key", [])) == dedup_key:
            return True
    return False


def _make_signal(
    signal: str,
    severity: str,
    dedup_key: tuple,
    metric_value: float,
    baseline_value: float,
    affected_keys: list[str],
    **extra: Any,
) -> dict:
    now = datetime.now(UTC)
    ttl_h = _TTL_HOURS.get(signal, 24)
    return {
        "signal": signal,
        "severity": severity,
        "metric_value": round(metric_value, 4),
        "baseline_value": round(baseline_value, 4),
        "delta_pct": round((metric_value - baseline_value) / max(baseline_value, 0.001) * 100),
        "affected_keys": affected_keys,
        "generated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=ttl_h)).isoformat(),
        "source": "ml-derived",
        "_dedup_key": list(dedup_key),
        **extra,
    }


# ── Signal detectors ──────────────────────────────────────────────────────────

def _detect_velocity_drop(
    velocity: dict | None,
    thresholds: dict,
    existing: list[dict],
) -> list[dict]:
    """Signal: recent velocity < rolling_mean - sigma * std_dev."""
    if not velocity:
        return []
    history = velocity.get("sprint_history") or velocity.get("story_points", {}).get("history", [])
    if len(history) < 3:
        return []
    sp_values = [float(e.get("completed_sp", 0)) for e in history if e.get("completed_sp") is not None]
    if len(sp_values) < 3:
        return []

    rolling = velocity.get("rolling_average") or (
        velocity.get("story_points", {}).get("avg_velocity")
    )
    std_dev = velocity.get("std_dev") or velocity.get("story_points", {}).get("std_dev")

    if rolling is None or std_dev is None or std_dev == 0:
        return []

    latest_sp = sp_values[-1]
    sigma = thresholds.get("velocity_drop_sigma", 2.0)
    threshold_value = float(rolling) - sigma * float(std_dev)

    if latest_sp >= threshold_value:
        return []

    sprint_id = history[-1].get("sprint_id") if history else "unknown"
    service_tag = "[all]"
    dedup_key = ("velocity_drop", service_tag, str(sprint_id))
    if _is_dedup("velocity_drop", dedup_key, existing):
        return []

    return [_make_signal(
        "velocity_drop", "warning", dedup_key,
        metric_value=latest_sp, baseline_value=float(rolling),
        affected_keys=[],
        service_tag=service_tag,
        sprint_id=sprint_id,
    )]


def _detect_carry_over_spike(
    outcomes_path: Path,
    thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: most recent sprint carry_over_rate > threshold."""
    if existing is None:
        existing = []
    if not outcomes_path.exists():
        return []

    records: list[dict] = []
    try:
        for line in outcomes_path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        return []

    if not records:
        return []

    # Find most recent sprint
    latest_sprint_id = records[-1].get("sprint_id")
    if latest_sprint_id is None:
        return []

    sprint_records = [r for r in records if r.get("sprint_id") == latest_sprint_id]
    if len(sprint_records) < 5:  # per-sprint guard
        return []

    # Group by service_tag
    by_tag: dict[str, list[dict]] = {}
    for r in sprint_records:
        tag = r.get("service_tag") or "[all]"
        if not tag.startswith("["):
            tag = f"[{tag}]"
        by_tag.setdefault(tag, []).append(r)

    signals = []
    threshold_pct = thresholds.get("carry_over_spike_pct", 0.40)

    for tag, recs in by_tag.items():
        carry_over_count = sum(1 for r in recs if r.get("outcome") == "carry_over")
        rate = carry_over_count / len(recs)
        if rate <= threshold_pct:
            continue

        dedup_key = ("carry_over_spike", tag, str(latest_sprint_id))
        if _is_dedup("carry_over_spike", dedup_key, existing):
            continue

        affected = [
            r["issue_key"] for r in recs
            if r.get("outcome") == "carry_over"
            and r.get("issue_key")
            and re.fullmatch(r"^[A-Z]+-\d+$", r["issue_key"])
        ]
        signals.append(_make_signal(
            "carry_over_spike", "warning", dedup_key,
            metric_value=rate, baseline_value=threshold_pct,
            affected_keys=affected[:10],
            service_tag=tag,
            sprint_id=latest_sprint_id,
        ))

    return signals


def _detect_wip_breach(
    snapshot: dict,
    board_config: dict,
    tracking: dict,
    _thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: WIP-limited column exceeds limit for >2 consecutive poll cycles."""
    if existing is None:
        existing = []
    columns = board_config.get("columns", {})
    signals = []

    for col_name, col_cfg in columns.items():
        wip_max = col_cfg.get("wip_max")
        if wip_max is None:
            continue
        statuses = col_cfg.get("statuses", [col_name])
        count = sum(
            1 for v in snapshot.values()
            if v.get("status") in statuses
        )
        if count > wip_max:
            entry = tracking.setdefault(col_name, {"count": 0, "last_seen": ""})
            entry["count"] += 1
            entry["last_seen"] = datetime.now(UTC).isoformat()

            if entry["count"] >= 3:
                dedup_key = ("wip_breach", col_name)
                if not _is_dedup("wip_breach", dedup_key, existing):
                    affected = [
                        k for k, v in snapshot.items()
                        if v.get("status") in statuses
                    ]
                    signals.append(_make_signal(
                        "wip_breach", "warning", dedup_key,
                        metric_value=float(count), baseline_value=float(wip_max),
                        affected_keys=affected[:10],
                        column=col_name,
                    ))
        else:
            # Reset tracking on recovery
            tracking.pop(col_name, None)

    return signals


def _detect_stagnant_issues(
    snapshot: dict,
    thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: issue In Progress > stagnant_days without status change."""
    if existing is None:
        existing = []
    stagnant_days = thresholds.get("stagnant_days_default", 7)
    overrides = thresholds.get("stagnant_days_override", {})
    now = datetime.now(UTC)
    signals = []

    for key, v in snapshot.items():
        if v.get("status") != "In Progress":
            continue
        status_since_str = v.get("status_since", "")
        if not status_since_str:
            continue
        try:
            ts = datetime.fromisoformat(status_since_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            age_days = (now - ts).total_seconds() / 86400
        except (ValueError, AttributeError):
            continue

        tag = v.get("service_tag", "")
        threshold = float(overrides.get(tag, stagnant_days))
        if age_days <= threshold:
            continue

        dedup_key = ("stagnant_issue", key)
        if _is_dedup("stagnant_issue", dedup_key, existing):
            continue

        signals.append(_make_signal(
            "stagnant_issue", "warning", dedup_key,
            metric_value=round(age_days, 1), baseline_value=threshold,
            affected_keys=[key],
        ))

    return signals


def _detect_sp_mismatch(
    snapshot: dict,
    thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: subtask SP sum > mismatch_pct x parent_sp after grace period."""
    if existing is None:
        existing = []
    sp_pct = thresholds.get("sp_mismatch_pct", 1.5)
    grace_hours = thresholds.get("sp_mismatch_grace_hours", 4)
    now = datetime.now(UTC)
    signals = []

    # Find parents In Progress past grace period
    parents_in_progress: dict[str, dict] = {}
    for key, v in snapshot.items():
        if v.get("status") != "In Progress":
            continue
        if v.get("issuetype") in ("Sub-task", "Subtask"):
            continue
        status_since_str = v.get("status_since", "")
        if not status_since_str:
            continue
        try:
            ts = datetime.fromisoformat(status_since_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            hours_in_progress = (now - ts).total_seconds() / 3600
        except (ValueError, AttributeError):
            continue
        if hours_in_progress > grace_hours:
            parent_sp = v.get("sp") or 0
            if parent_sp and parent_sp > 0:
                parents_in_progress[key] = {"sp": float(parent_sp)}

    if not parents_in_progress:
        return []

    # Sum subtask SP per parent
    subtask_sp: dict[str, float] = {}
    for key, v in snapshot.items():
        parent_key = v.get("parent")
        if parent_key and parent_key in parents_in_progress:
            sp = v.get("sp") or 0
            subtask_sp[parent_key] = subtask_sp.get(parent_key, 0.0) + float(sp)

    for parent_key, parent_data in parents_in_progress.items():
        total_sub_sp = subtask_sp.get(parent_key, 0.0)
        if total_sub_sp == 0:
            continue
        parent_sp = parent_data["sp"]
        if total_sub_sp <= sp_pct * parent_sp:
            continue

        dedup_key = ("sp_mismatch", parent_key)
        if _is_dedup("sp_mismatch", dedup_key, existing):
            continue

        signals.append(_make_signal(
            "sp_mismatch", "warning", dedup_key,
            metric_value=total_sub_sp, baseline_value=sp_pct * parent_sp,
            affected_keys=[parent_key],
            parent_sp=parent_sp,
        ))

    return signals


# ── Main entry ────────────────────────────────────────────────────────────────

def analyze(
    _diff: list[dict],
    new_snapshot: dict,
    old_snapshot: dict,
    calibration: dict,
    board_config: dict,
    velocity: dict | None,
    outcomes_path: Path = _OUTCOMES_FILE,
    insights_path: Path = _INSIGHTS_FILE,
    stop_event: threading.Event | None = None,
) -> None:
    """Detect signals and write insights.json. Safe to call from daemon thread."""
    if stop_event and stop_event.is_set():
        return

    thresholds = calibration.get("signal_thresholds", _DEFAULT_THRESHOLDS)
    state = _load_insights(insights_path)
    existing = state.get("signals", [])
    tracking = state.get("wip_breach_tracking", {})

    # Use old_snapshot (enriched, has status_since) for stagnant detection
    stagnant_snap = old_snapshot if old_snapshot else new_snapshot

    new_signals: list[dict] = []
    new_signals.extend(_detect_velocity_drop(velocity, thresholds, existing))
    new_signals.extend(_detect_carry_over_spike(outcomes_path, thresholds, existing))
    new_signals.extend(_detect_wip_breach(new_snapshot, board_config, tracking, thresholds, existing))
    new_signals.extend(_detect_stagnant_issues(stagnant_snap, thresholds, existing))
    new_signals.extend(_detect_sp_mismatch(new_snapshot, thresholds, existing))

    if stop_event and stop_event.is_set():
        return

    all_signals = _evict(existing + new_signals)
    state["signals"] = all_signals
    state["wip_breach_tracking"] = tracking

    _write_insights(insights_path, state)
