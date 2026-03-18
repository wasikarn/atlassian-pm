#!/usr/bin/env python3
"""Transition guard: Validate issue transition before execution.

PreToolUse hook for jira_transition_issue.
Injects context reminding Claude to verify the transition is valid.
Does not block — just adds context about HR6 requirement.

Exit codes: 0 (always — advisory only)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context

_HOOK = "pre-transition-guard"


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    tool_input = data.get("tool_input", {})
    issue_key = tool_input.get("issue_key", "?")
    transition = tool_input.get("transition", "?")

    inject_context(
        f"TRANSITION: {issue_key} → '{transition}'. "
        f"Verify: (1) transition is valid for current status "
        f"(use jira_get_transitions if unsure), "
        f"(2) HR6: run cache_invalidate(issue_key='{issue_key}', auto_refresh=true) after transition."
    )


if __name__ == "__main__":
    main()
