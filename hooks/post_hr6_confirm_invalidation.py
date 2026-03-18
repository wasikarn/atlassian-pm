#!/usr/bin/env python3
"""HR6: Clear pending state after cache_invalidate is called.

PostToolUse hook for cache_invalidate.
Removes the invalidated key from pending state so reads are unblocked.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import get_issue_key, log_event
from hooks_state import hr6_remove_pending

_HOOK = "hr6-invalidate-clear"


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

    hr6_remove_pending(session_id, issue_key)
    log_event(_HOOK, "CLEARED", {"issue_key": issue_key, "session_id": session_id})
    print("{}")


if __name__ == "__main__":
    main()
