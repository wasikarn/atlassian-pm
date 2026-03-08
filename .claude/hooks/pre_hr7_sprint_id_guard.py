#!/usr/bin/env python3
"""HR7: Block hardcoded sprint IDs — always lookup first.

PreToolUse hook for jira_create_issue and jira_update_issue.
If sprint field (customfield_10020) is set but no sprint lookup
was done in this session, blocks the operation.

Exit codes: 0 = allow, 2 = deny
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import log_event
from hooks_state import hr7_is_lookup_done

_HOOK = "hr7-sprint-id-guard"
SPRINT_FIELD = "customfield_10020"


def has_sprint_field(obj: object) -> bool:
    """Check if any dict contains sprint custom field."""
    if isinstance(obj, dict):
        if SPRINT_FIELD in obj:
            return True
        return any(has_sprint_field(v) for v in obj.values())
    if isinstance(obj, list):
        return any(has_sprint_field(v) for v in obj)
    return False


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    session_id = data.get("session_id", "")
    tool_input = data.get("tool_input", {})

    if not has_sprint_field(tool_input):
        print("{}")
        return

    if hr7_is_lookup_done(session_id):
        log_event(_HOOK, "ALLOWED", {"session_id": session_id})
        print("{}")
        return

    issue_key = tool_input.get("issue_key", "new")
    log_event(_HOOK, "BLOCKED", {"issue_key": issue_key, "session_id": session_id})
    reason = (
        f"HR7 BLOCKED: Sprint ID detected for {issue_key} but no sprint lookup in this session.\n"
        f"Run: jira_get_sprints_from_board(board_id=2, state='active') first.\n"
        f"HR7: Never hardcode sprint IDs — they change every sprint."
    )
    print(reason, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
