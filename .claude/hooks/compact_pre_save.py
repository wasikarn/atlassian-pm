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

try:
    data = json.loads(sys.stdin.read())
except Exception:
    data = {}

session_id = data.get("session_id", "default")
state_file = Path(f"/tmp/claude-hooks-state/{session_id}.json")
snapshot_file = Path(f"/tmp/claude-hooks-state/{session_id}.pre-compact.json")

if not state_file.exists():
    sys.exit(0)

try:
    state = json.loads(state_file.read_text())
except Exception:
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
print(
    f"Pre-compact snapshot saved: {pending_count} pending operations, session={session_id}",
    file=sys.stderr,
)
