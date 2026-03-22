#!/usr/bin/env python3
"""HR6: Track cache_invalidate for acli Jira commands run via Bash.

PostToolUse hook for Bash tool. Detects `acli jira workitem` commands
(create, edit, assign) and records pending cache invalidation.

acli bypasses MCP hooks, so this hook catches Jira writes made via CLI.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, get_issue_keys_from_text, get_tool_response, inject_context, log_event, parse_stdin
from hooks_state import hr6_add_pending

_HOOK = "hr6-acli-invalidate-track"

# Patterns that indicate a Jira write via acli
ACLI_WRITE_PATTERNS = [
    r"acli\s+jira\s+workitem\s+(create|edit|assign)",
    r"acli\s+jira\s+issue\s+(update|create|delete|assign|transition|comment)",
]


def main() -> None:
    data = parse_stdin()
    if not data:
        log_event(_HOOK, "SKIP", {})
        allow()
        return

    tool_name = data.get("tool_name", "")
    session_id = data.get("session_id", "")

    if tool_name != "Bash":
        log_event(_HOOK, "SKIP", {"reason": "wrong_tool", "tool": tool_name, "session_id": session_id})
        allow()
        return

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Check if this is an acli jira write command
    is_jira_write = any(re.search(p, command) for p in ACLI_WRITE_PATTERNS)
    if not is_jira_write:
        log_event(_HOOK, "SKIP", {"reason": "not_jira_write", "session_id": session_id})
        allow()
        return

    # Extract issue keys from command and output
    tool_output = get_tool_response(data)
    all_text = command + " " + tool_output

    keys = get_issue_keys_from_text(all_text)
    if not keys:
        # Try uppercase extraction from filenames like tasks/bep-123.json
        keys = get_issue_keys_from_text(all_text.upper())

    if not keys:
        log_event(_HOOK, "SKIP", {"reason": "no_keys_found", "session_id": session_id})
        allow()
        return

    unique_keys = list(dict.fromkeys(keys))

    for key in unique_keys:
        hr6_add_pending(session_id, key)

    log_event(_HOOK, "TRACKED", {"issue_keys": unique_keys, "session_id": session_id})

    keys_str = ", ".join(unique_keys)
    invalidate_calls = " + ".join(
        f"cache_invalidate(issue_key='{k}', auto_refresh=true)" for k in unique_keys
    )
    inject_context(
        f"HR6 REQUIRED (acli): Run {invalidate_calls} "
        f"before any subsequent read of {keys_str}. "
        f"acli commands bypass MCP hooks — cache invalidation is still required. "
        f"Stale cache causes silent data corruption."
    )


if __name__ == "__main__":
    main()
