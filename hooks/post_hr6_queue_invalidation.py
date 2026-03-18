#!/usr/bin/env python3
"""HR6: Track and enforce cache_invalidate after every Jira write.

PostToolUse hook for ALL Jira write operations:
  - jira_create_issue, jira_update_issue, jira_transition_issue
  - jira_create_issue_link, jira_remove_issue_link
  - jira_create_remote_issue_link
  - jira_add_comment, jira_add_worklog
  - jira_delete_issue, jira_link_to_epic

Records pending invalidation in session state (hr6-read-guard blocks stale reads)
and injects additionalContext reminder.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context, log_event
from hooks_state import hr6_add_pending

_HOOK = "hr6-cache-invalidate"


def extract_issue_keys(data: dict) -> list[str]:
    """Extract issue key(s) from tool_input or tool_response.

    Returns a list because some tools affect multiple issues
    (e.g. jira_create_issue_link affects both inward and outward issues).
    """
    keys: list[str] = []
    tool_name = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    # --- Issue link tools: both sides need invalidation ---
    if "issue_link" in tool_name and "remote" not in tool_name:
        for field in ("inward_issue_key", "outward_issue_key"):
            if field in inp:
                keys.append(str(inp[field]))
        if keys:
            return keys

    # --- Epic link: epic + all child issues ---
    if "link_to_epic" in tool_name:
        if "epic_key" in inp:
            keys.append(str(inp["epic_key"]))
        issue_keys = inp.get("issue_keys", [])
        if isinstance(issue_keys, list):
            keys.extend(str(k) for k in issue_keys)
        elif isinstance(issue_keys, str):
            keys.append(issue_keys)
        if keys:
            return keys

    # --- Standard: try tool_response first (create returns key) ---
    resp = data.get("tool_response", {})
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except (json.JSONDecodeError, TypeError):
            resp = {}
    if isinstance(resp, dict) and resp.get("key"):
        return [resp["key"]]

    # --- Standard: try tool_input (update/transition/comment/worklog) ---
    for field in ("issue_key", "issue_key_or_id", "key"):
        if field in inp:
            return [str(inp[field])]

    return []


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    issue_keys = extract_issue_keys(data)
    if not issue_keys:
        print("{}")
        return

    session_id = data.get("session_id", "")
    tool_name = data.get("tool_name", "unknown")

    for key in issue_keys:
        hr6_add_pending(session_id, key)

    log_event(_HOOK, "REMIND", {"issue_keys": issue_keys, "tool": tool_name, "session_id": session_id})

    keys_str = ", ".join(issue_keys)
    invalidate_calls = " + ".join(
        f"cache_invalidate(issue_key='{k}', auto_refresh=true)" for k in issue_keys
    )
    inject_context(
        f"HR6 REQUIRED: Run {invalidate_calls} "
        f"before any subsequent read of {keys_str}. "
        f"auto_refresh=true fetches fresh data in the same call (saves 1 MCP round-trip). "
        f"Stale cache causes silent data corruption."
    )


if __name__ == "__main__":
    main()
