#!/usr/bin/env python3
"""HR3: Block MCP assignee updates — use acli only.

PreToolUse hook for mcp__mcp-atlassian__jira_update_issue.
MCP assignee silently succeeds but does nothing. Always use acli.

Exit codes: 0 = allow, 2 = deny
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, block, log_event, parse_stdin

_HOOK = "hr3-block-mcp-assignee"
ASSIGNEE_KEYS = {"assignee", "assignee_id", "assignee_account_id"}


def has_assignee(obj: object) -> bool:
    """Recursively check if any dict contains assignee-related keys."""
    if isinstance(obj, dict):
        if ASSIGNEE_KEYS & {k.lower() for k in obj}:
            return True
        return any(has_assignee(v) for v in obj.values())
    if isinstance(obj, list):
        return any(has_assignee(v) for v in obj)
    return False


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    issue_key = tool_input.get("issue_key", "?")
    sid = data.get("session_id", "")

    if has_assignee(tool_input):
        log_event(_HOOK, "BLOCKED", {"issue_key": issue_key, "session_id": sid})
        reason = (
            f"HR3 BLOCKED: MCP assignee silently fails for {issue_key}. "
            'Use: acli jira workitem assign -k "KEY" -a "email" -y'
        )
        block(reason)
        return

    log_event(_HOOK, "ALLOWED", {"issue_key": issue_key, "session_id": sid})
    allow()


if __name__ == "__main__":
    main()
