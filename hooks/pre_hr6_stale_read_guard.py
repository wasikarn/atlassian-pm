#!/usr/bin/env python3
"""HR6: Block cache reads when invalidation is pending.

PreToolUse hook for cache_get_issue.
If a key has pending cache invalidation, blocks the read and forces
cache_invalidate first.

Exit codes: 0 = allow, 2 = deny
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import get_issue_key, log_event
from hooks_state import hr6_get_pending

_HOOK = "hr6-read-guard"


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    session_id = data.get("session_id", "")
    issue_key = get_issue_key(data.get("tool_input", {}))

    if not issue_key:
        print("{}")
        return

    pending = hr6_get_pending(session_id)
    if issue_key in pending:
        log_event(_HOOK, "BLOCKED", {"issue_key": issue_key, "session_id": session_id})
        reason = (
            f"HR6 BLOCKED: Cannot read {issue_key} — cache invalidation pending.\n"
            f"Run: cache_invalidate(issue_key='{issue_key}') first, then retry."
        )
        print(reason, file=sys.stderr)
        sys.exit(2)

    log_event(_HOOK, "ALLOWED", {"issue_key": issue_key, "session_id": session_id})
    print("{}")


if __name__ == "__main__":
    main()
