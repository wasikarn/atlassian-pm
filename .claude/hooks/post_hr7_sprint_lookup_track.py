#!/usr/bin/env python3
"""HR7: Track sprint lookups to validate sprint ID usage.

PostToolUse hook for jira_get_sprints_from_board.
Records that a sprint lookup was done in this session.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import log_event
from hooks_state import hr7_mark_lookup_done

_HOOK = "hr7-sprint-lookup-tracker"


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    session_id = data.get("session_id", "")
    hr7_mark_lookup_done(session_id)
    log_event(_HOOK, "TRACKED", {"session_id": session_id})
    print("{}")


if __name__ == "__main__":
    main()
