#!/usr/bin/env python3
"""HR5: Auto-clear parent verification when parent is confirmed.

PostToolUse hook for mcp__mcp-atlassian__jira_get_issue.
If the issue read matches a pending child key and parent is found,
automatically clears the pending verification.

Exit 0 = always allow
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hooks_state import hr5_get_pending, hr5_remove_pending

raw = sys.stdin.read()
data = json.loads(raw)
tool_input = data.get("tool_input", {})
tool_output = str(data.get("tool_output", ""))
session_id = data.get("session_id", "")

issue_key = tool_input.get("issue_key", "")
if not issue_key:
    sys.exit(0)

pending = hr5_get_pending(session_id)
pending_child = next((p for p in pending if p["child"] == issue_key), None)
if not pending_child:
    sys.exit(0)

expected_parent = pending_child["parent"]

if expected_parent in tool_output:
    hr5_remove_pending(session_id, issue_key)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"✅ HR5 verified: {issue_key} parent={expected_parent} confirmed. Cleared from pending."
            ),
        }
    }
    print(json.dumps(output))
else:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"⚠️ HR5 WARNING: {issue_key} expected parent {expected_parent} "
                f"NOT found in response! Subtask may be orphaned. "
                f"Fix: recreate subtask with correct parent field."
            ),
        }
    }
    print(json.dumps(output))

sys.exit(0)
