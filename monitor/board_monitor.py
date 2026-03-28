#!/usr/bin/env python3
"""Autonomous Jira board monitor.

Polls Jira every POLL_INTERVAL seconds. Detects changes, dispatches handlers.

Usage:
    python3 monitor/board_monitor.py
    python3 monitor/board_monitor.py --interval 300 --dry-run
    python3 monitor/board_monitor.py --once --dry-run
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

from monitor.handlers import issue_changed, pr_sync, sprint_health
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
    fields = "summary,status,assignee,priority,sprint"

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
                }
            total = response.get("total", 0)
            start_at += len(issues)
            if start_at >= total or not issues:
                break
    except Exception as e:
        log.error("Failed to fetch board snapshot: %s", e)
        return {}

    return result


def run_cycle(
    jira: JiraAPI,
    state: MonitorState,
    board_config: dict,
    project_key: str,
    dry_run: bool = False,
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

        state.save_snapshot(new_snapshot)
    else:
        log.info("[DRY RUN] %d changes detected, no writes", len(changes))
        for c in changes[:5]:
            log.info("  %s: %s", c["key"], list(c.get("changed_fields", {}).keys()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlassian-pm autonomous board monitor")
    parser.add_argument("--interval", type=int, default=300)
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

    log.info(
        "Monitor started. Project: %s, site: %s, interval: %ds, dry_run: %s",
        project_key, site, args.interval, args.dry_run,
    )

    if args.once:
        run_cycle(jira, state, board_config, project_key, dry_run=args.dry_run)
        return

    while True:
        try:
            run_cycle(jira, state, board_config, project_key, dry_run=args.dry_run)
            time.sleep(args.interval)
        except KeyboardInterrupt:
            log.info("Monitor stopped by user")
            break
        except Exception as e:
            log.error("Cycle error: %s", e)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
