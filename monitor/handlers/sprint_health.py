#!/usr/bin/env python3
"""Handler c2: check WIP limits and sprint end date, send iMessage alert."""

import contextlib
import os
import subprocess
from datetime import date, datetime
from typing import Any


def _send_imessage(message: str) -> None:
    """Send alert via iMessage using osascript."""
    number = os.environ.get("ATLASSIAN_PM_ALERT_NUMBER", "")
    if not number:
        return
    script = f'tell application "Messages" to send "{message}" to buddy "{number}"'
    with contextlib.suppress(subprocess.TimeoutExpired, FileNotFoundError):
        subprocess.run(["osascript", "-e", script], timeout=5, check=False)


def handle(board_config: dict[str, Any], issues: list[dict[str, Any]]) -> list[str]:
    """Check WIP limits and sprint end. Return list of alert messages sent."""
    alerts = []
    columns = board_config.get("columns", {})

    for col_name, col_config in columns.items():
        wip_max = col_config.get("wip_max")
        if wip_max is None:
            continue
        statuses = col_config.get("statuses", [])
        count = sum(1 for i in issues if i.get("status") in statuses)
        if count > wip_max:
            msg = f"⚠️ WIP LIMIT: {col_name} has {count}/{wip_max} issues."
            _send_imessage(msg)
            alerts.append(msg)

    for issue in issues:
        sprint_end = issue.get("sprint_end_date")
        if not sprint_end:
            continue
        try:
            end = datetime.fromisoformat(sprint_end).date()
            days_left = (end - date.today()).days
            if 0 <= days_left <= 2:
                msg = f"⏰ SPRINT ENDS in {days_left} day(s) ({end})."
                _send_imessage(msg)
                alerts.append(msg)
                break
        except ValueError:
            continue

    return alerts
