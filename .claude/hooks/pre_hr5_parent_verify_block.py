#!/usr/bin/env python3
"""HR5: Block subtask creation if parent verification is pending.

PreToolUse hook for mcp__mcp-atlassian__jira_create_issue.
Blocks further subtask creates if a previous subtask's parent link
hasn't been verified yet.

Exit codes: 0 = allow, 2 = block (pending verification)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hooks_state import hr5_get_pending

raw = sys.stdin.read()
data = json.loads(raw)
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")

# Check if this is a subtask creation (has parent field)
additional = tool_input.get("additional_fields", {})
if isinstance(additional, str):
    try:
        additional = json.loads(additional)
    except (json.JSONDecodeError, TypeError):
        additional = {}

has_parent = bool(additional.get("parent")) or bool(tool_input.get("parent"))
if not has_parent:
    sys.exit(0)

# Check for pending parent verifications (filter out UNKNOWN = failed creates)
pending = [p for p in hr5_get_pending(session_id) if p.get("child") != "UNKNOWN"]
if pending:
    children = ", ".join(p["child"] for p in pending)
    parents = ", ".join(f"{p['child']}→{p['parent']}" for p in pending)
    print(
        f"HR5 BLOCKED: Verify parent links before creating more subtasks.\n"
        f"Pending: {parents}\n"
        f"Run: jira_get_issue(issue_key='KEY', fields='parent,summary') for each pending child.\n"
        f"After verification, you may continue creating subtasks.",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
