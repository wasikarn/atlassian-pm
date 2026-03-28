#!/usr/bin/env python3
"""Handler: detect sprint closure and update velocity in project-config-team-detail.json.

Triggered when a sprint transitions to "closed" state. Calculates:
  - SP completed in that sprint
  - Appends to sprint_history
  - Recalculates rolling_average (last 5 sprints)
  - Calculates trend_pct = (avg_last_3 - avg_prev_3) / avg_prev_3 * 100
  - Calculates std_dev from last 5 sprints
  - Updates last_updated_sprint
"""

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_TEAM_DETAIL_FILENAME = "project-config-team-detail.json"
_VELOCITY_STATE_KEY = "velocity"
_HISTORY_KEY = "sprint_history"
_ROLLING_WINDOW = 5
_TREND_WINDOW = 3

# Guard against re-processing the same sprint in one daemon run
_processed_sprint_ids: set[int] = set()


# ── Config file discovery ─────────────────────────────────────────────────────

def _find_team_detail_config(start_dir: Path) -> Path | None:
    """Walk up from start_dir looking for .claude/project-config-team-detail.json."""
    current = start_dir.resolve()
    for _ in range(10):  # max 10 levels up
        candidate = current / ".claude" / _TEAM_DETAIL_FILENAME
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _load_config(config_path: Path) -> dict:
    """Load JSON config, return empty dict on error."""
    try:
        return json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(config_path: Path, data: dict) -> bool:
    """Save JSON config. Returns True on success."""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return True
    except OSError as e:
        log.error("Failed to write %s: %s", config_path, e)
        return False


# ── Statistics helpers ────────────────────────────────────────────────────────

def _rolling_average(values: list[float], window: int) -> float | None:
    """Mean of the last `window` values, or None if the list is empty."""
    if not values:
        return None
    recent = values[-window:]
    return sum(recent) / len(recent)


def _std_dev(values: list[float], window: int) -> float | None:
    """Sample std dev of the last `window` values, or None if < 2 values."""
    recent = values[-window:]
    n = len(recent)
    if n < 2:
        return None
    mean = sum(recent) / n
    variance = sum((x - mean) ** 2 for x in recent) / (n - 1)
    return math.sqrt(variance)


def _trend_pct(values: list[float], window: int = _TREND_WINDOW) -> float | None:
    """% change from prev-window avg to last-window avg.

    Returns None when there are fewer than 2*window data points.
    Formula: (avg_last_N - avg_prev_N) / avg_prev_N * 100
    """
    if len(values) < 2 * window:
        return None
    prev = values[-(2 * window):-window]
    last = values[-window:]
    avg_prev = sum(prev) / len(prev)
    avg_last = sum(last) / len(last)
    if avg_prev == 0:
        return None
    return (avg_last - avg_prev) / avg_prev * 100


# ── Core update function ──────────────────────────────────────────────────────

def update_velocity_from_sprint(
    sprint_data: dict,
    config_path: Path | None = None,
) -> bool:
    """Update velocity config from a completed sprint.

    Args:
        sprint_data: Dict with keys: sprint_id (int), completed_sp (float),
                     total_sp (float), date (ISO string).
        config_path: Explicit path to project-config-team-detail.json.
                     Falls back to walking up from cwd when None.

    Returns:
        True if the config file was updated, False otherwise.
    """
    sprint_id = sprint_data.get("sprint_id")
    completed_sp = sprint_data.get("completed_sp")
    date_str = sprint_data.get("date", "")

    if sprint_id is None or completed_sp is None:
        log.warning("update_velocity_from_sprint: missing sprint_id or completed_sp")
        return False

    # Resolve config path
    if config_path is None:
        config_path = _find_team_detail_config(Path.cwd())
        if config_path is None:
            log.warning("project-config-team-detail.json not found; skipping velocity update")
            return False

    config = _load_config(config_path)

    # Ensure velocity section exists
    velocity: dict = config.setdefault(_VELOCITY_STATE_KEY, {})
    history: list = velocity.setdefault(_HISTORY_KEY, [])

    # Avoid duplicate sprint entries
    if any(e.get("sprint_id") == sprint_id for e in history):
        log.info("Sprint %s already recorded in velocity history; skipping", sprint_id)
        return False

    # Append new record
    history.append({
        "sprint_id": sprint_id,
        "completed_sp": completed_sp,
        "total_sp": sprint_data.get("total_sp"),
        "date": date_str,
    })

    # Recalculate derived metrics
    sp_values = [float(e["completed_sp"]) for e in history if e.get("completed_sp") is not None]

    velocity["rolling_average"] = _rolling_average(sp_values, _ROLLING_WINDOW)
    velocity["std_dev"] = _std_dev(sp_values, _ROLLING_WINDOW)
    velocity["trend_pct"] = _trend_pct(sp_values, _TREND_WINDOW)
    velocity["last_updated_sprint"] = sprint_id
    velocity["sprints_tracked"] = len(history)

    log.info(
        "Velocity updated: sprint=%s completed_sp=%.1f rolling_avg=%.1f trend_pct=%s",
        sprint_id,
        float(completed_sp),
        velocity["rolling_average"] or 0,
        f"{velocity['trend_pct']:.1f}%" if velocity["trend_pct"] is not None else "n/a",
    )

    return _save_config(config_path, config)


# ── Sprint-closure detection ──────────────────────────────────────────────────

def _collect_sprint_sp(jira: Any, sprint_id: int, project_key: str, sp_field: str) -> tuple[float, float]:
    """Fetch all issues in the sprint and return (completed_sp, total_sp).

    Completed means status category = Done.
    """
    completed = 0.0
    total = 0.0
    start_at = 0
    page_size = 50

    try:
        while True:
            resp = jira.get_sprint_issues(
                sprint_id,
                fields=f"summary,status,{sp_field}",
                max_results=page_size,
                start_at=start_at,
            )
            issues = resp.get("issues", [])
            for issue in issues:
                fields = issue.get("fields", {})
                sp = fields.get(sp_field) or fields.get("customfield_10016") or 0
                try:
                    sp = float(sp)
                except (TypeError, ValueError):
                    sp = 0.0
                total += sp
                status_cat = (
                    (fields.get("status") or {})
                    .get("statusCategory", {})
                    .get("name", "")
                )
                if status_cat.lower() in ("done", "complete"):
                    completed += sp
            fetched = len(issues)
            start_at += fetched
            if fetched < page_size or start_at >= resp.get("total", 0):
                break
    except Exception as e:
        log.error("Failed to collect sprint SP for sprint %s: %s", sprint_id, e)

    return completed, total


def check_and_update_velocity(
    jira: Any,
    board_config: dict,
    root_dir: Path,
) -> bool:
    """Detect newly closed sprints and update velocity config.

    Args:
        jira:         JiraAPI instance.
        board_config: The board section from project-config.json.
        root_dir:     Repo root (used to find project-config-team-detail.json).

    Returns:
        True if the velocity config was updated.
    """
    board_id = board_config.get("kanban_board_id") or board_config.get("board_id")
    if not board_id:
        return False

    try:
        result = jira.get_board_sprints(board_id, state="closed")
        closed_sprints = result.get("values", [])
    except Exception as e:
        log.warning("Could not fetch closed sprints: %s", e)
        return False

    if not closed_sprints:
        return False

    # Find the most recently closed sprint that we haven't processed yet
    # Jira returns sprints in ascending order; take the last one.
    latest_closed = closed_sprints[-1]
    sprint_id = latest_closed.get("id")

    if sprint_id in _processed_sprint_ids:
        return False

    _processed_sprint_ids.add(sprint_id)

    # Try to find team detail config
    config_path = _find_team_detail_config(root_dir)
    if config_path is None:
        log.info("No project-config-team-detail.json found; skipping velocity update for sprint %s", sprint_id)
        return False

    # Load project-config.json to get SP field name and project key
    project_config_path = root_dir / ".claude" / "project-config.json"
    if not project_config_path.exists():
        project_config_path = root_dir.parent.parent / ".claude" / "project-config.json"

    project_key = "TP"
    sp_field = "customfield_10016"
    try:
        proj_cfg = json.loads(project_config_path.read_text())
        project_key = proj_cfg.get("jira", {}).get("project_key", project_key)
        sp_field = proj_cfg.get("jira", {}).get("custom_fields", {}).get("story_points", sp_field)
    except (json.JSONDecodeError, OSError):
        pass

    completed_sp, total_sp = _collect_sprint_sp(jira, sprint_id, project_key, sp_field)

    end_date = latest_closed.get("endDate", "")
    if end_date:
        # Normalise to ISO date portion only
        end_date = end_date[:10]
    else:
        from datetime import date
        end_date = date.today().isoformat()

    sprint_data = {
        "sprint_id": sprint_id,
        "completed_sp": completed_sp,
        "total_sp": total_sp,
        "date": end_date,
    }

    return update_velocity_from_sprint(sprint_data, config_path=config_path)
