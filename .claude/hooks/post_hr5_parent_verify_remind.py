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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context, log_event

_HOOK = "hr5-verify-parent"
CACHE_DB = Path.home() / ".cache" / "jira-generator" / "jira.db"


def extract_parent(tool_input: dict) -> str | None:
    """Extract parent key from additional_fields or direct field."""
    # Check additional_fields (most common path)
    additional = tool_input.get("additional_fields", {})
    if isinstance(additional, str):
        try:
            additional = json.loads(additional)
        except (json.JSONDecodeError, TypeError):
            additional = {}

    parent = additional.get("parent", {})
    if isinstance(parent, dict):
        return parent.get("key")
    if isinstance(parent, str):
        return parent

    # Check direct parent field
    parent = tool_input.get("parent", {})
    if isinstance(parent, dict):
        return parent.get("key")
    if isinstance(parent, str):
        return parent

    return None


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
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    tool_input = data.get("tool_input", {})
    parent_key = extract_parent(tool_input)

    # Only fire for subtask creation (has parent)
    if not parent_key:
        print("{}")
        return

    issue_key = extract_issue_key(data)
    session_id = data.get("session_id", "")

    # If no key returned, creation failed — nothing to verify
    if not issue_key:
        log_event(_HOOK, "SKIP", {"reason": "no_issue_key_in_response", "parent_key": parent_key})
        print("{}")
        return

    # Save to state for blocker + auto-clear hooks
    try:
        from hooks_state import hr5_add_known_subtask, hr5_add_pending

        hr5_add_pending(session_id, issue_key, parent_key)
        hr5_add_known_subtask(session_id, issue_key)
    except Exception:
        pass

    # Enrich cache DB so HR10 can detect subtask cross-session
    try:
        conn = sqlite3.connect(str(CACHE_DB))
        conn.execute(
            "UPDATE issues SET issue_type = 'Subtask', parent_key = ? WHERE issue_key = ? AND (issue_type IS NULL OR issue_type = '')",
            (parent_key, issue_key),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

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
