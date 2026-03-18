#!/usr/bin/env python3
"""Cache-checked-tracker: Mark issue as cache-checked after cache_get_issue.

PostToolUse hook — when cache_get_issue is called, marks the issue key
in session state so that cache-prefer.py (PreToolUse) allows subsequent
jira_get_issue calls for the same key (cache miss fallback).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import get_issue_key
from hooks_state import cache_mark_checked


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    session_id = data.get("session_id", "")
    issue_key = get_issue_key(data.get("tool_input", {}))

    if issue_key:
        cache_mark_checked(session_id, issue_key)

    print("{}")


if __name__ == "__main__":
    main()
