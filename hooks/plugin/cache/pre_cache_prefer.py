#!/usr/bin/env python3
"""Cache-prefer: Block jira_get_issue if cache hasn't been tried first.

PreToolUse hook — when Claude calls jira_get_issue:
1. Extract issue_key from tool_input
2. Check if cache_get_issue was already tried for this key
3. If not tried → block with suggestion to use cache first
4. If already tried (cache miss) → allow MCP fallback

Exit 0 = allow, Exit 2 = block with cache suggestion
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, block, get_issue_key, log_event, parse_stdin
from hooks_state import cache_is_checked

_HOOK = "cache-prefer"


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        allow()
        return

    # Only intercept jira_get_issue
    if "jira_get_issue" not in data.get("tool_name", ""):
        log_event(_HOOK, "SKIP", {"reason": "wrong_tool", "tool": data.get("tool_name", "")})
        allow()
        return

    session_id = data.get("session_id", "")
    issue_key = get_issue_key(data.get("tool_input", {}))

    if not issue_key:
        log_event(_HOOK, "SKIP", {"reason": "no_issue_key", "session_id": session_id})
        allow()
        return

    # Check if cache was already tried for this issue
    if cache_is_checked(session_id, issue_key):
        # Cache was tried — allow MCP fallback
        log_event(_HOOK, "ALLOWED", {"issue_key": issue_key, "session_id": session_id})
        allow()
        return

    # Cache NOT tried — block and suggest
    log_event(_HOOK, "BLOCKED", {"issue_key": issue_key, "session_id": session_id})
    block(
        f"CACHE-FIRST: Try cache_get_issue(issue_key='{issue_key}') before "
        f"calling jira_get_issue. If cache miss, retry jira_get_issue.\n"
        f"Reason: Local cache is faster and reduces Jira API load."
    )


if __name__ == "__main__":
    main()
