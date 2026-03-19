#!/usr/bin/env python3
"""Search-before-create: Block issue creation if no search was done first.

PreToolUse hook for jira_create_issue / jira_batch_create_issues.
Blocks (exit 2) if no jira_search was performed in this session.

Exit codes: 0 = pass, 2 = block
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_state import search_is_done

_HOOK = "pre-search-before-create"


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    session_id = data.get("session_id", "")

    if search_is_done(session_id):
        sys.exit(0)

    # Subtasks are children of an existing story — dedup search not required
    tool_input = data.get("tool_input", {})
    issuetype = (tool_input.get("issuetype") or "").lower()
    if "sub" in issuetype:
        sys.exit(0)

    # Block: no search done yet
    print(
        "DEDUP BLOCK: Cannot create issues without prior search in this session. "
        "Run jira_search(jql='project = BEP AND summary ~ \"keyword\"', "
        "fields='summary,status,issuetype', limit=10) or /jira-search-issues first. "
        "This prevents duplicate issues.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
