#!/usr/bin/env python3
"""SessionStart hook: surface pending stuck issues detected by the board monitor.

Reads the stuck_issues.json queue written by monitor/handlers/stuck_issue_detector.py.
If pending items exist, injects a warning into the session context so Claude knows
to flag them. Moves items from 'pending' → 'surfaced' to avoid re-surfacing every session.

Exit code: always 0 (SessionStart must not block startup).
"""

import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import inject_context, log_event

_HOOK = "stuck-issues-notify"

DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)
STUCK_FILE = DATA_DIR / "stuck_issues.json"


def _load(path: Path) -> dict:
    if not path.exists():
        return {"rate_limit": {}, "pending": [], "surfaced": []}
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return {"rate_limit": {}, "pending": [], "surfaced": []}
        data.setdefault("rate_limit", {})
        data.setdefault("pending", [])
        data.setdefault("surfaced", [])
        return data
    except (json.JSONDecodeError, OSError):
        return {"rate_limit": {}, "pending": [], "surfaced": []}


def _save(path: Path, data: dict) -> None:
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    data = _load(STUCK_FILE)
    pending = data.get("pending", [])
    if not pending:
        return

    # Build warning message
    lines = [f"⚠️ {len(pending)} stuck issue(s) detected by board monitor:"]
    for item in pending:
        key = item.get("issue_key", "?")
        status = item.get("status", "?")
        age = item.get("age_days", 0)
        summary = item.get("summary", "")
        assignee = item.get("assignee", "")
        line = f"  • {key} — {status} for {age:.1f}d"
        if summary:
            line += f": {summary}"
        if assignee:
            line += f" (assignee: {assignee})"
        lines.append(line)
    lines.append("Run /atlassian-pm:apm-status to review and take action.")

    inject_context("\n".join(lines), event_name="SessionStart")
    log_event(_HOOK, "INFO", {"surfaced_count": len(pending)})

    # Move pending → surfaced so they don't repeat every session
    now_iso = datetime.now(UTC).isoformat()
    for item in pending:
        data["surfaced"].append({**item, "surfaced_at": now_iso})
    data["pending"] = []
    _save(STUCK_FILE, data)


if __name__ == "__main__":
    main()
