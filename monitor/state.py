#!/usr/bin/env python3
"""Monitor state: snapshot persistence and diff detection."""

import json
from pathlib import Path
from typing import Any


class MonitorState:
    """Persist Jira board snapshot between poll cycles."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))

    def load_snapshot(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}


def diff_snapshots(
    old: dict[str, Any],
    new: dict[str, Any],
    tracked_fields: tuple[str, ...] = ("status", "assignee", "priority", "summary"),
) -> list[dict[str, Any]]:
    """Return list of change events between two board snapshots."""
    changes = []
    for key, new_issue in new.items():
        if key not in old:
            changes.append({"key": key, "is_new": True, "changed_fields": {}, "issue": new_issue})
            continue
        old_issue = old[key]
        changed = {}
        for field in tracked_fields:
            old_val = old_issue.get(field)
            new_val = new_issue.get(field)
            if old_val != new_val:
                changed[field] = (old_val, new_val)
        if changed:
            changes.append({"key": key, "is_new": False, "changed_fields": changed, "issue": new_issue})
    return changes
