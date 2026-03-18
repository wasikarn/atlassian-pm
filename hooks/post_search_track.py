#!/usr/bin/env python3
"""Search tracker: Record that a Jira search was done in this session.

PostToolUse hook for jira_search.
Used by search-before-create to verify dedup was attempted.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_state import search_mark_done


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    session_id = data.get("session_id", "")
    search_mark_done(session_id)
    print("{}")


if __name__ == "__main__":
    main()
