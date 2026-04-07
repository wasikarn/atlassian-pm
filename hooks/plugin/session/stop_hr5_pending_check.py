#!/usr/bin/env python3
"""P7: HR5 Stop Hook — check for tasks with unverified parents.

Stop hook (no matcher — runs every turn end).
Reads HR5 pending state written by post_hr5_parent_verify_remind.py.
If any task keys are pending (parent not verified via jira_get_issue),
blocks the turn end with a reminder.

HR5 pending is cleared by post_hr5_parent_verify_clear.py which fires
on jira_get_issue and calls hr5_remove_pending.

Exit: print {"ok": true/false, "reason": "..."} to stdout
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event, parse_stdin
from hooks_state import hr5_get_pending

_HOOK = "p7-hr5-stop-check"


def check_pending(pending: list) -> dict:
    """Return {"ok": true} or {"ok": false, "reason": ...}.

    `pending` is a list of dicts with "child" and "parent" keys,
    as returned by hr5_get_pending().
    """
    if not pending:
        return {"ok": True}
    keys = ", ".join(sorted(p["child"] for p in pending))
    return {
        "ok": False,
        "reason": (
            f"HR5: Task parent unverified for: {keys}. "
            f"Run jira_get_issue for each to confirm parent.key is set. "
            f"If parent is correct, the pending state will clear automatically."
        ),
    }


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

    # Fast-path: Check if DB exists before querying
    from hooks_state import STATE_DIR
    db_path = STATE_DIR / f"{session_id}.db"
    if not db_path.exists():
        print(json.dumps({"ok": True}))
        return

    pending = hr5_get_pending(session_id, fast_mode=True)

    result = check_pending(pending)
    if result["ok"]:
        log_event(_HOOK, "ALLOWED", {"reason": "no_pending", "session_id": session_id})
    else:
        log_event(_HOOK, "BLOCKED", {"pending_keys": [p["child"] for p in pending], "session_id": session_id})

    print(json.dumps(result))


if __name__ == "__main__":
    main()
