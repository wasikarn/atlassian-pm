#!/usr/bin/env python3
"""Search tracker: Record that a Jira search was done in this session.

PostToolUse hook for jira_search.
Used by search-before-create to verify dedup was attempted.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, log_event, parse_stdin
from hooks_state import search_mark_done

_HOOK = "search-track"


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        allow()
        return

    session_id = data.get("session_id", "")
    search_mark_done(session_id)
    log_event(_HOOK, "TRACKED", {"session_id": session_id})
    allow()


if __name__ == "__main__":
    main()
