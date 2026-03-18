#!/usr/bin/env python3
"""Cache-prefer: Block jira_get_issue if cache hasn't been tried first.

PreToolUse hook — when Claude calls jira_get_issue:
1. Extract issue_key from tool_input
2. Check if cache_get_issue was already tried for this key
3. If not tried → block with suggestion to use cache first
4. If already tried (cache miss) → allow MCP fallback

Exit 0 = allow, Exit 2 = block with cache suggestion
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import get_issue_key
from hooks_state import cache_is_checked


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    # Only intercept jira_get_issue
    if "jira_get_issue" not in data.get("tool_name", ""):
        print("{}")
        return

    session_id = data.get("session_id", "")
    issue_key = get_issue_key(data.get("tool_input", {}))

    if not issue_key:
        print("{}")
        return

    # Check if cache was already tried for this issue
    if cache_is_checked(session_id, issue_key):
        # Cache was tried — allow MCP fallback
        print("{}")
        return

    # Cache NOT tried — block and suggest
    msg = (
        f"CACHE-FIRST: Try cache_get_issue(issue_key='{issue_key}') before "
        f"calling jira_get_issue. If cache miss, retry jira_get_issue.\n"
        f"Reason: Local cache is faster and reduces Jira API load."
    )
    print(msg, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
