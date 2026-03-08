#!/usr/bin/env python3
"""HR6: Track cache_invalidate for acli Jira commands run via Bash.

PostToolUse hook for Bash tool. Detects `acli jira workitem` commands
(create, edit, assign) and records pending cache invalidation.

acli bypasses MCP hooks, so this hook catches Jira writes made via CLI.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context
from hooks_state import hr6_add_pending

# Patterns that indicate a Jira write via acli
ACLI_WRITE_PATTERNS = [
    r"acli\s+jira\s+workitem\s+(create|edit|assign)",
    r"acli\s+jira\s+issue\s+(update|create|delete|assign)",
]


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        print("{}")
        return

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Check if this is an acli jira write command
    is_jira_write = any(re.search(p, command) for p in ACLI_WRITE_PATTERNS)
    if not is_jira_write:
        print("{}")
        return

    # Extract issue keys from command and output
    tool_output = str(data.get("tool_output", ""))
    all_text = command + " " + tool_output

    keys = re.findall(r"[A-Z]+-\d+", all_text)
    if not keys:
        # Try uppercase extraction from filenames like tasks/bep-123.json
        keys = re.findall(r"[A-Z]+-\d+", all_text.upper())

    if not keys:
        print("{}")
        return

    unique_keys = list(dict.fromkeys(keys))
    session_id = data.get("session_id", "")

    for key in unique_keys:
        hr6_add_pending(session_id, key)

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
