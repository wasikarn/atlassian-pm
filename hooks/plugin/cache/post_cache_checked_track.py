#!/usr/bin/env python3
"""Cache-checked-tracker: Mark issue as cache-checked after cache_get_issue.

PostToolUse hook — when cache_get_issue is called, marks the issue key
in session state so that cache-prefer.py (PreToolUse) allows subsequent
jira_get_issue calls for the same key (cache miss fallback).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, get_issue_key, log_event, parse_stdin
from hooks_state import cache_mark_checked

_HOOK = "cache-checked-track"


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        return

    session_id = data.get("session_id", "")
    issue_key = get_issue_key(data.get("tool_input", {}))

    if issue_key:
        cache_mark_checked(session_id, issue_key)
        log_event(_HOOK, "TRACKED", {"issue_key": issue_key, "session_id": session_id})
    else:
        log_event(_HOOK, "SKIP", {"reason": "no_issue_key", "session_id": session_id})

    allow()


if __name__ == "__main__":
    main()
