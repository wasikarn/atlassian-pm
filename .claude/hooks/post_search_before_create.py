#!/usr/bin/env python3
"""Search-before-create: Remind to search for duplicates before creating issues.

PostToolUse hook for jira_create_issue.
Checks if jira_search was called in this session. If not, injects reminder.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context, log_event
from hooks_state import search_is_done

_HOOK = "search-before-create"


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    session_id = data.get("session_id", "")

    if search_is_done(session_id):
        print("{}")
        return

    # Extract created issue info
    resp = data.get("tool_response", {})
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except (json.JSONDecodeError, TypeError):
            resp = {}
    issue_key = resp.get("key", "?") if isinstance(resp, dict) else "?"

    log_event(_HOOK, "WARN", {"issue_key": issue_key, "session_id": session_id})
    inject_context(
        f"DEDUP WARNING: {issue_key} created without prior search in this session. "
        f"Verify no duplicates exist. Use /jira-search-issues or "
        f"jira_search(jql='project = BEP AND summary ~ \"keyword\"') "
        f"before creating issues."
    )


if __name__ == "__main__":
    main()
