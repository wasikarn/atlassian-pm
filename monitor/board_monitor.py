#!/usr/bin/env python3
"""Autonomous Jira board monitor.

Polls Jira every POLL_INTERVAL seconds. Detects changes, dispatches handlers.

Usage:
    python3 monitor/board_monitor.py
    python3 monitor/board_monitor.py --interval 300 --dry-run
    python3 monitor/board_monitor.py --once --dry-run
"""

import argparse
import datetime
import json
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

from monitor.handlers import issue_changed, pr_sync, sprint_health
from monitor.handlers import stuck_issue_detector, velocity_feed
from monitor.state import MonitorState, diff_snapshots

_LOG_DIR = _ROOT / "monitor" / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [monitor] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(_LOG_DIR / "monitor.log"),
    ],
)
log = logging.getLogger(__name__)

_STATE_PATH = Path.home() / ".claude" / "monitor-state.json"
_CALIBRATION_FILE = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
) / "calibration.json"
_OUTCOMES_FILE = _CALIBRATION_FILE.parent / "story-outcomes.jsonl"
_PID_FILE = Path.home() / ".claude" / "atlassian-pm-monitor.pid"

_stop_event = threading.Event()
_last_analyzer_thread: threading.Thread | None = None


def _get_poll_interval(board_state: dict, config: dict) -> int:
    """Return poll interval in seconds based on board activity level.

    Priority (highest wins):
      weekend           → 900 s  (15 min)
      off-hours (local) → 600 s  (10 min)
      active sprint     → 120 s  ( 2 min)
      default           → 300 s  ( 5 min)
    """
    now = datetime.datetime.now()

    is_weekend = now.weekday() >= 5
    is_off_hours = now.hour < 8 or now.hour >= 20

    if is_weekend:
        return 900
    if is_off_hours:
        return 600

    active_sprint = board_state.get("active_sprint")
    if active_sprint:
        return 120

    return 300


def fetch_board_snapshot(jira: JiraAPI, project_key: str) -> dict[str, Any]:
    """Fetch all non-Done issues and return as key → fields dict.

    search_issues returns the full Jira search response dict; the issue list
    is at result['issues']. fields is a comma-separated string. max_results
    is capped at 50 per call by the API, so we paginate if needed.
    """
    result = {}
    start_at = 0
    page_size = 50
    jql = f"project = {project_key} AND statusCategory != Done ORDER BY updated DESC"
    fields = "summary,status,assignee,priority,sprint,issuetype,parent,customfield_10016"

    try:
        while True:
            response = jira.search_issues(
                jql=jql,
                fields=fields,
                max_results=page_size,
                start_at=start_at,
            )
            issues = response.get("issues", [])
            for issue in issues:
                key = issue.get("key", "")
                f = issue.get("fields", {})
                sprint_field = f.get("sprint") or f.get("customfield_10020")
                sprint_end = None
                if sprint_field:
                    if isinstance(sprint_field, list):
                        sprint_field = sprint_field[-1]  # last sprint = most recent
                    sprint_end = sprint_field.get("endDate") if isinstance(sprint_field, dict) else None
                result[key] = {
                    "summary": f.get("summary", ""),
                    "status": (f.get("status") or {}).get("name", ""),
                    "assignee": ((f.get("assignee") or {}).get("displayName", "")),
                    "priority": ((f.get("priority") or {}).get("name", "")),
                    "sprint_end_date": sprint_end,
                    "issuetype": ((f.get("issuetype") or {}).get("name", "")),
                    "parent": ((f.get("parent") or {}).get("key")),
                    "sp": f.get("customfield_10016") or f.get("customfield_10036"),
                }
            total = response.get("total", 0)
            start_at += len(issues)
            if start_at >= total or not issues:
                break
    except Exception as e:
        log.error("Failed to fetch board snapshot: %s", e)
        return {}

    return result


def _detect_active_sprint(jira: JiraAPI, board_id: int) -> dict | None:
    """Return the active sprint dict (id, name, endDate) or None if none active."""
    try:
        result = jira.get_board_sprints(board_id, state="active")
        sprints = result.get("values", [])
        return sprints[0] if sprints else None
    except Exception:
        return None


def run_cycle(
    jira: JiraAPI,
    state: MonitorState,
    board_config: dict,
    project_key: str,
    dry_run: bool = False,
    poll_count: int = 0,
) -> None:
    """Single poll cycle: fetch → diff → dispatch handlers."""
    old_snapshot = state.load_snapshot()
    new_snapshot = fetch_board_snapshot(jira, project_key)

    if not new_snapshot:
        log.warning("Empty snapshot — skipping cycle")
        return

    changes = diff_snapshots(old_snapshot, new_snapshot)
    log.info("Cycle: %d issues, %d changes", len(new_snapshot), len(changes))

    if not dry_run:
        for change in changes[:10]:
            if issue_changed.handle(change, jira):
                log.info("Commented on %s", change["key"])

        issues_list = [
            {"status": v["status"], "sprint_end_date": v.get("sprint_end_date")}
            for v in new_snapshot.values()
        ]
        alerts = sprint_health.handle(board_config, issues_list)
        if alerts:
            log.info("Sent %d health alerts", len(alerts))

        synced = pr_sync.handle(jira)
        if synced:
            log.info("Synced PRs for: %s", ", ".join(synced))

        # Stuck issue detection: run every 3rd poll or when there are issue changes
        if poll_count % 3 == 0 or changes:
            try:
                created = stuck_issue_detector.check_stuck_issues(new_snapshot, state, jira)
                if created:
                    log.info("Stuck detector created follow-up tasks: %s", ", ".join(created))
            except Exception as e:
                log.error("Stuck issue detector failed: %s", e)

        # Velocity feed: run when sprint state has changed to closed
        try:
            velocity_feed.check_and_update_velocity(jira, board_config, _ROOT)
        except Exception as e:
            log.error("Velocity feed failed: %s", e)

        # Enrich snapshot with status-entry timestamps before saving so stuck
        # detector can measure staleness across cycles.
        enriched = new_snapshot  # fallback if enrichment fails
        try:
            enriched = stuck_issue_detector.enrich_snapshot_with_status_since(new_snapshot, state)
            state.save_snapshot(enriched)
        except Exception as e:
            log.error("Failed to enrich/save snapshot: %s", e)
            state.save_snapshot(new_snapshot)
        _dispatch_analyzer(changes, enriched, old_snapshot, board_config=board_config, dry_run=dry_run)
    else:
        log.info("[DRY RUN] %d changes detected, no writes", len(changes))
        for c in changes[:5]:
            log.info("  %s: %s", c["key"], list(c.get("changed_fields", {}).keys()))


def _load_calibration() -> dict:
    """Load calibration.json. Returns empty dict on missing/error."""
    try:
        return json.loads(_CALIBRATION_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _load_velocity(root: Path) -> dict | None:
    """Load velocity section from project-config-team-detail.json."""
    config_path = root / ".claude" / "project-config-team-detail.json"
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text())
        return data.get("velocity")
    except (json.JSONDecodeError, OSError):
        return None


def _write_pid() -> None:
    """Write current PID to lockfile. Check for stale lock first."""
    if _PID_FILE.exists():
        try:
            stored_pid = int(_PID_FILE.read_text().strip())
            os.kill(stored_pid, 0)  # 0 = liveness check only
            log.error("Monitor already running (pid=%d). Exiting.", stored_pid)
            sys.exit(1)
        except (ValueError, ProcessLookupError):
            log.warning("Stale lock detected (pid from file). Clearing.")
        except PermissionError:
            # PermissionError means the process IS alive (cross-user). Not stale.
            log.error("Monitor already running (pid=%d, PermissionError). Exiting.", stored_pid)
            sys.exit(1)
    try:
        _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PID_FILE.write_text(str(os.getpid()))
    except OSError as e:
        log.warning("Could not write PID file: %s", e)


def _cleanup_pid() -> None:
    """Delete PID file on exit."""
    try:
        _PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _sigterm_handler(signum: int, frame: object) -> None:
    """Handle SIGTERM: signal stop, join analyzer thread, cleanup."""
    global _last_analyzer_thread
    log.info("SIGTERM received — shutting down")
    _stop_event.set()
    if _last_analyzer_thread and _last_analyzer_thread.is_alive():
        _last_analyzer_thread.join(timeout=3)
    # Clean up any in-flight .tmp file
    tmp = _CALIBRATION_FILE.parent / "insights.tmp"
    if tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass
    _cleanup_pid()
    sys.exit(0)


def _dispatch_analyzer(
    changes: dict,
    snapshot: dict,
    old_snapshot: dict,
    *,
    board_config: dict,
    dry_run: bool = False,
) -> None:
    """Dispatch intelligence_analyzer in a daemon thread."""
    global _last_analyzer_thread
    if dry_run:
        return
    from monitor.handlers import intelligence_analyzer
    calibration = _load_calibration()
    velocity = _load_velocity(_ROOT)
    t = threading.Thread(
        target=intelligence_analyzer.analyze,
        args=(changes, snapshot, old_snapshot),
        kwargs={
            "calibration": calibration,
            "board_config": board_config,
            "velocity": velocity,
            "outcomes_path": _OUTCOMES_FILE,
            "stop_event": _stop_event,
        },
        daemon=True,
    )
    t.start()
    _last_analyzer_thread = t


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlassian-pm autonomous board monitor")
    parser.add_argument(
        "--interval", type=int, default=0,
        help="Poll interval in seconds. 0 (default) = adaptive (120/300/600/900 based on time/sprint).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()

    # In worktrees, .claude/project-config.json may only exist in the common git dir.
    # Try local first, then walk up to the git common dir (worktree parent).
    config_path = _ROOT / ".claude" / "project-config.json"
    if not config_path.exists():
        # For worktrees: check common git directory two levels up
        common_dir = _ROOT.parent.parent / ".claude" / "project-config.json"
        if common_dir.exists():
            config_path = common_dir
    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.error("Cannot read project-config.json: %s", e)
        sys.exit(1)

    project_key = config["jira"]["project_key"]
    site = config["jira"]["site"]
    board_config = config.get("board", {})

    try:
        creds = load_credentials()
        # derive_jira_url strips /wiki suffix from the Confluence URL
        base_url = derive_jira_url(creds["CONFLUENCE_URL"])
        auth_header = get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"])
        ssl_ctx = create_ssl_context()
        jira = JiraAPI(base_url, auth_header, ssl_ctx)
    except Exception as e:
        log.error("Auth failed: %s", e)
        sys.exit(1)

    state = MonitorState(_STATE_PATH)

    signal.signal(signal.SIGTERM, _sigterm_handler)
    _write_pid()

    board_id = config.get("jira", {}).get("board_id") or config.get("board", {}).get("kanban_board_id")

    log.info(
        "Monitor started. Project: %s, site: %s, board_id: %s, interval: %s, dry_run: %s",
        project_key, site, board_id,
        "adaptive" if args.interval == 0 else f"{args.interval}s",
        args.dry_run,
    )

    if args.once:
        run_cycle(jira, state, board_config, project_key, dry_run=args.dry_run, poll_count=0)
        return

    poll_count = 0
    board_state: dict = {}

    while True:
        try:
            # Refresh active sprint info for adaptive interval calculation
            if board_id:
                active_sprint = _detect_active_sprint(jira, board_id)
                board_state = {"active_sprint": active_sprint}
            else:
                board_state = {}

            run_cycle(
                jira, state, board_config, project_key,
                dry_run=args.dry_run, poll_count=poll_count,
            )
            poll_count += 1

            interval = (
                args.interval
                if args.interval > 0
                else _get_poll_interval(board_state, config)
            )
            log.info("Next poll in %ds", interval)
            time.sleep(interval)
        except KeyboardInterrupt:
            log.info("Monitor stopped by user")
            _cleanup_pid()
            break
        except Exception as e:
            log.error("Cycle error: %s", e)
            fallback = args.interval if args.interval > 0 else 300
            time.sleep(fallback)


if __name__ == "__main__":
    main()
