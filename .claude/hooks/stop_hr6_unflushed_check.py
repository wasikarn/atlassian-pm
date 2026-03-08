#!/usr/bin/env python3
"""HR6 Stop Hook: Check for pending cache invalidations at session end.

Replaces the prompt-based stop hook with a deterministic Python check.
Reads session state file and reports any pending cache invalidations.

If the jira-cache-server process is not running, pending state is auto-cleared
(no cache = no stale risk) and the session is allowed to end.

Output: {"ok": true} or {"ok": false, "reason": "..."}
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_state import hr6_clear_all_pending, hr6_get_pending


def is_cache_server_running() -> bool:
    """Check if the jira-cache-server process is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "jira-cache-server/server.py"],
            capture_output=True,
            timeout=2,
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"ok": True}))
        return

    session_id = data.get("session_id", "")
    pending = hr6_get_pending(session_id)

    if not pending:
        print(json.dumps({"ok": True}))
        return

    # Pending exists — check if server is running before blocking
    if not is_cache_server_running():
        hr6_clear_all_pending(session_id)
        print(json.dumps({"ok": True}))
        return

    keys = ", ".join(sorted(pending))
    print(
        json.dumps(
            {
                "ok": False,
                "reason": (
                    f"HR6: cache_invalidate missing for: {keys}. "
                    f"Run cache_invalidate for each before ending session."
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
