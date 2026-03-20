#!/usr/bin/env python3
"""DoD enforcement: block jira_transition_issue if transitioning to Done/Ready without explicit DoD confirmation.

Checks for DoD confirmation signal in environment. If not present, blocks with reminder.
DoD confirmation signal: CLAUDE_DOD_CONFIRMED=<issue_key> env var set by Claude after manual check.
"""
import json
import os
import sys


def main():
    tool_input_raw = os.environ.get("TOOL_INPUT", "{}")
    try:
        tool_input = json.loads(tool_input_raw)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True}))
        return

    issue_key = tool_input.get("issue_key", "")
    transition = str(tool_input.get("transition", tool_input.get("transition_id", ""))).lower()

    # Only check for Done/Ready transitions
    done_keywords = ["done", "ready", "waiting to test", "closed", "resolved"]
    if not any(kw in transition for kw in done_keywords):
        print(json.dumps({"continue": True}))
        return

    # Check if DoD was already confirmed for this issue
    confirmed = os.environ.get("CLAUDE_DOD_CONFIRMED", "")
    if confirmed == issue_key:
        print(json.dumps({"continue": True}))
        return

    # Block with DoD checklist
    reason = (
        f"⛔ DoD Check required before transitioning {issue_key} to '{transition}'.\n\n"
        "Before proceeding, verify ALL of the following:\n"
        "  1. All subtasks of this issue are in 'Done' status\n"
        "  2. If this is a Story: a QA subtask exists and is Done\n"
        "  3. Development info shows at least one PR link (check jira_get_issue_development_info)\n"
        "  4. No subtask is still 'In Progress'\n\n"
        "If all checks pass → set env CLAUDE_DOD_CONFIRMED={issue_key} and retry the transition.\n"
        "If any check fails → fix the issue before transitioning."
    ).format(issue_key=issue_key)

    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
