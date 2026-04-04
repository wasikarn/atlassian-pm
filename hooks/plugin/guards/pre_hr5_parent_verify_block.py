#!/usr/bin/env python3
"""HR5: Block task creation if parent verification is pending.

PreToolUse hook for mcp__mcp-atlassian__jira_create_issue.
Blocks further task creates if a previous task's parent link
hasn't been verified yet.

Exit codes: 0 = allow, 1 = block (pending verification)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import get_parent_key, parse_stdin
from hooks_state import cleanup_stale_state, hr5_get_pending

data = parse_stdin()
if not data:
    sys.exit(0)
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")

# Check if this is a child task creation (has parent field)
has_parent = bool(get_parent_key(tool_input))
if not has_parent:
    sys.exit(0)

# Clean stale pending entries before checking
cleanup_stale_state(session_id)

# Check for pending parent verifications (filter out UNKNOWN = failed creates)
pending = [p for p in hr5_get_pending(session_id) if p.get("child") != "UNKNOWN"]
if pending:
    children = ", ".join(p["child"] for p in pending)
    parents = ", ".join(f"{p['child']}→{p['parent']}" for p in pending)
    print(
        f"HR5 BLOCKED: Verify parent links before creating more tasks.\n"
        f"Pending: {parents}\n"
        f"Run: jira_get_issue(issue_key='KEY', fields='parent,summary') for each pending child.\n"
        f"After verification, you may continue creating tasks.",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
