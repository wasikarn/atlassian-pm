#!/usr/bin/env python3
"""HR5: Remind to verify parent link after subtask creation.

PostToolUse hook for mcp__mcp-atlassian__jira_create_issue.
Only fires when the create had a parent field (subtask creation).
Injects additionalContext reminder to verify the parent link.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, get_parent_key, inject_context, log_event, parse_stdin

_HOOK = "hr5-verify-parent"
CACHE_DB = Path.home() / ".cache" / "atlassian-pm" / "atlassian.db"


def extract_issue_key(data: dict) -> str | None:
    """Extract created issue key from tool_response."""
    resp = data.get("tool_response", {})
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except (json.JSONDecodeError, TypeError):
            resp = {}
    if isinstance(resp, dict):
        return resp.get("key")
    return None


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    parent_key = get_parent_key(tool_input)

    # Only fire for subtask creation (has parent)
    if not parent_key:
        allow()
        return

    issue_key = extract_issue_key(data)
    session_id = data.get("session_id", "")

    # If no key returned, creation failed — nothing to verify
    if not issue_key:
        log_event(_HOOK, "SKIP", {"reason": "no_issue_key_in_response", "parent_key": parent_key})
        allow()
        return

    # Save to state for blocker + auto-clear hooks
    try:
        from hooks_state import hr5_add_known_subtask, hr5_add_pending

        hr5_add_pending(session_id, issue_key, parent_key)
        hr5_add_known_subtask(session_id, issue_key)
    except Exception as e:
        log_event(_HOOK, "ERROR", {"phase": "state_save", "issue_key": issue_key, "error": str(e)})

    # Enrich cache DB so HR10 can detect subtask cross-session
    try:
        conn = sqlite3.connect(str(CACHE_DB))
        conn.execute(
            "UPDATE issues SET issue_type = 'Subtask', parent_key = ? WHERE issue_key = ? AND (issue_type IS NULL OR issue_type = '')",
            (parent_key, issue_key),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log_event(_HOOK, "ERROR", {"phase": "cache_enrich", "issue_key": issue_key, "error": str(e)})

    log_event(_HOOK, "REMIND", {"issue_key": issue_key, "parent_key": parent_key, "session_id": session_id})
    inject_context(
        f"HR5 REQUIRED: Verify parent link for {issue_key}. "
        f"Expected parent: {parent_key}. "
        f"Run: jira_get_issue(issue_key='{issue_key}', fields='parent,summary') "
        f"and confirm parent.key == '{parent_key}'. "
        f"MCP may silently ignore the parent field — if missing, "
        f"the subtask is orphaned (HR5 violation)."
    )


if __name__ == "__main__":
    main()
