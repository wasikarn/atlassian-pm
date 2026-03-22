#!/usr/bin/env python3
"""Search-before-create: Block issue creation if no search was done first.

PreToolUse hook for jira_create_issue / jira_batch_create_issues.
Blocks (exit 2) if no jira_search was performed in this session.

Exit codes: 0 = pass, 2 = block
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config_loader import load_project_config
from hooks_lib import allow, block, log_event, parse_stdin
from hooks_state import search_is_done

_cfg = load_project_config()
_PROJECT_KEY = _cfg.get("jira", {}).get("project_key", "<project_key>")

_HOOK = "pre-search-before-create"


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        sys.exit(0)

    session_id = data.get("session_id", "")

    if search_is_done(session_id):
        log_event(_HOOK, "ALLOWED", {"reason": "search_done", "session_id": session_id})
        allow()
        return

    # Subtasks are children of an existing story — dedup search not required
    tool_input = data.get("tool_input", {})
    issuetype = (tool_input.get("issuetype") or "").lower()
    if "sub" in issuetype:
        log_event(_HOOK, "ALLOWED", {"reason": "subtask_exempt", "session_id": session_id})
        allow()
        return

    # Block: no search done yet
    log_event(_HOOK, "BLOCKED", {"reason": "no_search_done", "session_id": session_id})
    block(
        "DEDUP BLOCK: Cannot create issues without prior search in this session. "
        f"Run jira_search(jql='project = {_PROJECT_KEY} AND summary ~ \"keyword\"', "
        "fields='summary,status,issuetype', limit=10) or /jira-search-issues first. "
        "This prevents duplicate issues."
    )


if __name__ == "__main__":
    main()
