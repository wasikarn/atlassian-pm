#!/usr/bin/env python3
"""DoD enforcement: block jira_transition_issue if moving to Done without DoD confirmation.

Blocks unless CLAUDE_DOD_CONFIRMED=<issue_key> env var is set.

Exit codes: 0 (allow), 1 (block)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks_lib import allow, block, log_event, parse_stdin

_HOOK = "dod-check"
_DONE_KEYWORDS = frozenset(["done", "ready", "waiting to test", "closed", "resolved"])


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    issue_key = str(tool_input.get("issue_key", "")).upper()
    transition = str(tool_input.get("transition", tool_input.get("transition_id", ""))).lower()

    if not any(kw in transition for kw in _DONE_KEYWORDS):
        allow()
        return

    confirmed = os.environ.get("CLAUDE_DOD_CONFIRMED", "")
    if confirmed == issue_key:
        log_event(_HOOK, "ALLOWED", {"issue_key": issue_key, "transition": transition})
        allow()
        return

    reason = (
        f"⛔ DoD Check required before transitioning {issue_key} to '{transition}'.\n\n"
        "Before proceeding, verify ALL of the following:\n"
        "  1. All child tasks are Done\n"
        "  2. At least one PR link exists (jira_get_issue_development_info)\n"
        "  3. No child task is still In Progress\n\n"
        f"If all pass → set env CLAUDE_DOD_CONFIRMED={issue_key} and retry."
    )
    log_event(_HOOK, "BLOCKED", {"issue_key": issue_key, "transition": transition})
    block(reason)


if __name__ == "__main__":
    main()
