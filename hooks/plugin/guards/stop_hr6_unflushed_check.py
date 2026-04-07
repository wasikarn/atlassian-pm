#!/usr/bin/env python3
"""HR6 Stop Hook: Check for pending cache invalidations at session end.

Replaces the prompt-based stop hook with a deterministic Python check.
Reads session state file and reports any pending cache invalidations.

If the atlassian-cache process is not running, pending state is auto-cleared
(no cache = no stale risk) and the session is allowed to end.

Output: {"ok": true} or {"ok": false, "reason": "..."}
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event, parse_stdin
from hooks_state import hr6_clear_all_pending, hr6_get_pending, STATE_DIR

_HOOK = "hr6-stop-unflushed-check"


def is_cache_server_running() -> bool:
    """Check if the atlassian-cache process is running via PID file.

    Fast check using PID file แทน pgrep -f ซึ่งช้ามากเมื่อมี process เยอะ.
    """
    import os

    # Check PID file first (instant)
    try:
        pid_file = Path("/tmp/atlassian-cache.pid")
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            # Signal 0 = check if process exists (no actual signal sent)
            os.kill(pid, 0)
            return True
    except (OSError, ValueError):
        # Process doesn't exist or invalid PID file
        pass

    # Fallback: Check socket file
    try:
        socket_file = Path("/tmp/atlassian-cache.sock")
        if socket_file.exists():
            return True
    except Exception:
        pass

    # Last resort: fast pgrep without -f flag (only matches process name)
    try:
        result = subprocess.run(
            ["pgrep", "-x", "python3"],  # -x = exact match, faster than -f
            capture_output=True,
            timeout=0.5,
        )
        # If any python3 is running, assume cache server might be running
        # This is conservative but fast
        return result.returncode == 0
    except Exception:
        return False


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        print(json.dumps({"ok": True}))
        return

    session_id = data.get("session_id", "")
    if not session_id:
        print(json.dumps({"ok": True}))
        return

    # Fast-path: Check if DB exists before querying (avoids connection overhead)
    db_path = STATE_DIR / f"{session_id}.db"
    if not db_path.exists():
        print(json.dumps({"ok": True}))
        return

    pending = hr6_get_pending(session_id, fast_mode=True)

    if not pending:
        log_event(_HOOK, "ALLOWED", {"reason": "no_pending", "session_id": session_id})
        print(json.dumps({"ok": True}))
        return

    # Pending exists — check if server is running before blocking
    if not is_cache_server_running():
        hr6_clear_all_pending(session_id)
        log_event(_HOOK, "ALLOWED", {"reason": "cache_server_not_running", "session_id": session_id})
        print(json.dumps({"ok": True}))
        return

    keys = ", ".join(sorted(pending))
    log_event(_HOOK, "BLOCKED", {"pending_keys": list(pending), "session_id": session_id})
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
