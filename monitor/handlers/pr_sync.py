#!/usr/bin/env python3
"""Handler c3/c4: detect PR merge events from hook logs and sync Jira."""

import contextlib
import json
import logging
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_HOOKS_LOG_DIR = Path(os.environ.get("CLAUDE_PLUGIN_DATA",
                                      str(Path.home() / ".claude"))) / "hooks-logs"
_PROCESSED_FILE = Path(os.environ.get("CLAUDE_PLUGIN_DATA",
                                       str(Path.home() / ".claude"))) / "monitor-pr-processed.json"
_ISSUE_KEY_RE = re.compile(r"\b([A-Z]+-\d+)\b")


def _entry_ts(event_id: str) -> float:
    """Extract timestamp from event_id, return 0.0 if not parseable."""
    try:
        ts_str = event_id.split("-")[0]
        return float(ts_str)
    except (ValueError, IndexError):
        return 0.0


def _load_processed() -> set[str]:
    if not _PROCESSED_FILE.exists():
        return set()
    try:
        data = json.loads(_PROCESSED_FILE.read_text())
        cutoff = time.time() - 48 * 3600
        # entries are stored as "TIMESTAMP-url" — filter old ones
        return {e for e in data if _entry_ts(e) > cutoff}
    except (json.JSONDecodeError, OSError):
        return set()


def _save_processed(processed: set[str]) -> None:
    with contextlib.suppress(OSError):
        _PROCESSED_FILE.write_text(json.dumps(sorted(processed)))


def _find_new_pr_events(processed: set[str]) -> list[dict[str, Any]]:
    """Scan today's hook log for unprocessed post_pr_sync events."""
    log_file = _HOOKS_LOG_DIR / f"{date.today().isoformat()}.jsonl"
    if not log_file.exists():
        return []
    events = []
    try:
        for line in log_file.read_text().splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("hook") != "post-pr-sync":
                continue
            event_id = f"{entry.get('ts', '')}-{entry.get('pr_url', '')}"
            if event_id not in processed:
                events.append({**entry, "_event_id": event_id})
    except OSError:
        pass
    return events


def handle(jira_api: Any) -> list[str]:
    """Process new PR merge events. Return list of issue keys synced."""
    processed = _load_processed()
    events = _find_new_pr_events(processed)
    synced = []

    for event in events:
        pr_url = event.get("pr_url", "")
        branch = event.get("branch", "")
        keys = _ISSUE_KEY_RE.findall(branch) or _ISSUE_KEY_RE.findall(pr_url)
        if not keys:
            processed.add(event["_event_id"])
            continue
        issue_key = keys[0]
        try:
            comment = f"🔗 PR merged: {pr_url}" if pr_url else f"🔗 PR merged from branch: {branch}"
            jira_api.add_comment(issue_key, comment)
            transitions = jira_api.get_transitions(issue_key)
            done_id = next(
                (t["id"] for t in transitions if "done" in t["name"].lower()),
                None
            )
            if done_id:
                jira_api.transition_issue(issue_key, done_id)
            processed.add(event["_event_id"])
            synced.append(issue_key)
        except Exception as e:
            log.warning("PR sync failed for %s: %s", issue_key, e)

    _save_processed(processed)
    return synced
