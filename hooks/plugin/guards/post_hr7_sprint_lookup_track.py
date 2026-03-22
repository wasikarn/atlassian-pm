#!/usr/bin/env python3
"""HR7: Track sprint lookups to validate sprint ID usage.

PostToolUse hook for jira_get_sprints_from_board.
Records that a sprint lookup was done in this session.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, log_event, parse_stdin
from hooks_state import hr7_mark_lookup_done

_HOOK = "hr7-sprint-lookup-tracker"


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    session_id = data.get("session_id", "")
    hr7_mark_lookup_done(session_id)
    log_event(_HOOK, "TRACKED", {"session_id": session_id})
    allow()


if __name__ == "__main__":
    main()
