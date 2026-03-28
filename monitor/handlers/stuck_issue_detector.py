#!/usr/bin/env python3
"""Handler: detect issues stuck in the same status for too long.

Strategy: write stuck issues to a JSON file rather than calling the Jira API
directly — this keeps the daemon simple, avoids auth complexity, and lets a
skill/human process consume the file and create follow-up sub-tasks.

Stuck thresholds:
  "In Progress"  → > 3 days without status change
  "In Review"    → > 2 days without status change

Rate limit: one follow-up entry per issue per 7 days (tracked in the JSON file).
"""

import contextlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Configurable via env so tests can override without touching the filesystem.
_DEFAULT_STUCK_FILE = (
    Path(os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm")))
    / "stuck_issues.json"
)

_STUCK_THRESHOLDS: dict[str, int] = {
    "In Progress": 3,  # days
    "In Review": 2,    # days
}

_RATE_LIMIT_DAYS = 7   # minimum days between follow-up entries for the same issue
_DAY_SECS = 86_400


# ── State file helpers ────────────────────────────────────────────────────────

def _load_stuck_file(path: Path) -> dict:
    """Load the stuck-issues state file. Returns empty structure on any error."""
    if not path.exists():
        return {"rate_limit": {}, "pending": []}
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return {"rate_limit": {}, "pending": []}
        data.setdefault("rate_limit", {})
        data.setdefault("pending", [])
        return data
    except (json.JSONDecodeError, OSError):
        return {"rate_limit": {}, "pending": []}


def _save_stuck_file(path: Path, data: dict) -> None:
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ── Status entry tracking ─────────────────────────────────────────────────────

def _get_status_entry_time(issue_key: str, current_status: str, state: Any) -> float:
    """Return Unix timestamp when this issue entered its current status.

    Uses MonitorState snapshots to detect transitions. Falls back to *now* if
    the state history is unavailable, so new daemons never false-fire on startup.
    """
    try:
        old_snapshot = state.load_snapshot()
        old_issue = old_snapshot.get(issue_key)
        if old_issue is None:
            # Issue is new — treat entry time as now
            return time.time()
        if old_issue.get("status") != current_status:
            # Status just changed — entry time is now
            return time.time()
        # Status unchanged from last snapshot: retrieve the tracked entry time
        # stored in the snapshot's _status_since field (we write it below).
        entry_time = old_issue.get("_status_since")
        if isinstance(entry_time, (int, float)) and entry_time > 0:
            return float(entry_time)
        # No _status_since recorded yet (first run after upgrade) — treat as now
        return time.time()
    except Exception:
        return time.time()


def enrich_snapshot_with_status_since(snapshot: dict, state: Any) -> dict:
    """Add _status_since to each issue in the snapshot.

    Call this before saving the snapshot so the next cycle can measure staleness.
    Does not mutate the original dict.
    """
    now = time.time()
    enriched: dict = {}
    try:
        old_snapshot = state.load_snapshot()
    except Exception:
        old_snapshot = {}

    for key, fields in snapshot.items():
        old_issue = old_snapshot.get(key, {})
        current_status = fields.get("status", "")
        old_status = old_issue.get("status", "")
        old_since = old_issue.get("_status_since")

        if current_status != old_status or not isinstance(old_since, (int, float)):
            # Status changed or no previous record — reset the clock
            since = now
        else:
            since = float(old_since)

        enriched[key] = {**fields, "_status_since": since}

    return enriched


# ── Core detection ────────────────────────────────────────────────────────────

def check_stuck_issues(
    snapshot: dict,
    state: Any,
    jira_client: Any,
    stuck_file: Path | None = None,
) -> list[str]:
    """Check for stuck issues and record them for follow-up.

    Args:
        snapshot:    Current board snapshot (key → fields dict).
        state:       MonitorState instance for reading previous snapshots.
        jira_client: Unused — kept for API compatibility. Writes go to JSON file.
        stuck_file:  Override path to the stuck-issues JSON file (for testing).

    Returns:
        List of issue keys newly written to the stuck-issues file.
    """
    path = stuck_file if stuck_file is not None else _DEFAULT_STUCK_FILE
    file_data = _load_stuck_file(path)
    rate_limit: dict = file_data["rate_limit"]
    now = time.time()
    created: list[str] = []

    for issue_key, fields in snapshot.items():
        status = fields.get("status", "")
        threshold_days = _STUCK_THRESHOLDS.get(status)
        if threshold_days is None:
            continue

        # Prefer _status_since embedded in the snapshot (written by
        # enrich_snapshot_with_status_since). Fall back to state lookup
        # for snapshots that pre-date this feature.
        raw_since = fields.get("_status_since")
        if isinstance(raw_since, (int, float)) and raw_since > 0:
            entry_time = float(raw_since)
        else:
            entry_time = _get_status_entry_time(issue_key, status, state)
        age_days = (now - entry_time) / _DAY_SECS

        if age_days <= threshold_days:
            continue  # Not stuck yet

        # Rate limit: skip if we already flagged this issue recently
        last_flagged = rate_limit.get(issue_key, 0)
        if (now - last_flagged) < (_RATE_LIMIT_DAYS * _DAY_SECS):
            continue

        # Record the stuck issue
        summary = fields.get("summary", "")
        assignee = fields.get("assignee", "")
        label = "Review follow-up" if status == "In Review" else "Follow up"
        follow_up_summary = f"{label}: {summary} is stuck" if summary else f"{label}: {issue_key} is stuck"

        entry = {
            "issue_key": issue_key,
            "status": status,
            "age_days": round(age_days, 1),
            "summary": summary,
            "assignee": assignee,
            "follow_up_summary": follow_up_summary,
            "detected_at": now,
        }
        file_data["pending"].append(entry)
        rate_limit[issue_key] = now
        created.append(issue_key)
        log.info(
            "Stuck issue detected: %s (%s for %.1f days) → queued follow-up",
            issue_key, status, age_days,
        )

    if created:
        _save_stuck_file(path, file_data)

    return created
