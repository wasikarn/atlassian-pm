#!/usr/bin/env python3
"""Save state snapshot before compaction.

PreCompact hook — writes a snapshot file that post-compact-reinject.py
can reference. Also outputs state summary to stderr for debug logging.

Note: PreCompact stdout is NOT injected into context (only SessionStart
and UserPromptSubmit do). State is saved to a file for post-compact use.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event, parse_stdin

_HOOK = "compact-pre-save"


def main() -> None:
    data = parse_stdin() or {}

    session_id = data.get("session_id", "default")
    state_file = Path(f"/tmp/claude-hooks-state/{session_id}.json")
    snapshot_file = Path(f"/tmp/claude-hooks-state/{session_id}.pre-compact.json")

    if not state_file.exists():
        log_event(_HOOK, "SKIP", {"reason": "no_state_file", "session_id": session_id})
        sys.exit(0)

    try:
        state = json.loads(state_file.read_text())
    except Exception:
        log_event(_HOOK, "SKIP", {"reason": "state_read_error", "session_id": session_id})
        sys.exit(0)

    # Save snapshot with timestamp
    snapshot = {
        "timestamp": time.time(),
        "compaction_trigger": data.get("source", "unknown"),
        "state": state,
    }
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_text(json.dumps(snapshot, indent=2))

    # Log to stderr (visible in verbose/debug mode)
    pending_count = len(state.get("hr5_pending", [])) + len(state.get("hr6_pending", []))
    log_event(_HOOK, "TRACKED", {"pending_count": pending_count, "session_id": session_id})
    print(
        f"Pre-compact snapshot saved: {pending_count} pending operations, session={session_id}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
