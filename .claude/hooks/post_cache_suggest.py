#!/usr/bin/env python3
"""Cache-suggest: After jira_get_issue succeeds, remind to use cache first.

PostToolUse hook — tracks that MCP was used directly (without cache),
and marks the issue as cache-checked so the PreToolUse hook won't block
subsequent reads of the same issue.

Also auto-populates cache by suggesting cache_get_issue for warm-up.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import get_issue_key, inject_context
from hooks_state import cache_is_checked, cache_mark_checked


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    tool_name = data.get("tool_name", "")
    session_id = data.get("session_id", "")
    tool_input = data.get("tool_input", {})

    # Handle jira_get_issue — mark as checked + suggest
    if "jira_get_issue" in tool_name:
        issue_key = get_issue_key(tool_input)
        if issue_key and not cache_is_checked(session_id, issue_key):
            cache_mark_checked(session_id, issue_key)
            inject_context(
                f"Cache-first reminder: You used jira_get_issue directly for {issue_key}. "
                f"Next time, try cache_get_issue first for faster reads."
            )
            return

    # Handle jira_search — suggest cache_search/cache_text_search
    if "jira_search" in tool_name:
        jql = tool_input.get("jql", "")
        # Only suggest for simple key-based or parent-based queries
        if any(kw in jql.lower() for kw in ("key =", "key in", "parent =", "parent in")):
            inject_context(
                "Cache-first reminder: For key/parent-based JQL, consider using "
                "cache_search(jql=...) first for faster results."
            )
            return

    # Default: no additional context
    print("{}")


if __name__ == "__main__":
    main()
