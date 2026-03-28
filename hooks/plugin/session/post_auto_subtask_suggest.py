#!/usr/bin/env python3
"""PostToolUse hook: after creating a Story, suggest running subtask generation.

Fires after jira_create_issue succeeds. Checks if the created issue is a Story type.
If so, injects a context message suggesting the user run suggest_subtasks.py or
the create-story skill's subtask phase.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import parse_stdin, inject_context

STORY_TYPE_NAMES = {"story", "user story"}


def main():
    data = parse_stdin()
    # PostToolUse: data has tool_name, tool_input, tool_response
    tool_response = data.get("tool_response", {})
    tool_input = data.get("tool_input", {})

    # Only act on successful issue creation
    if not isinstance(tool_response, dict):
        return

    issue_key = tool_response.get("key") or tool_response.get("id")
    if not issue_key:
        return

    # Check issue type
    issue_type = tool_input.get("issuetype", {})
    if isinstance(issue_type, dict):
        type_name = issue_type.get("name", "").lower()
    else:
        type_name = str(issue_type).lower()

    if type_name not in STORY_TYPE_NAMES:
        return

    # Inject suggestion
    summary = tool_input.get("summary", "")
    inject_context(
        f"Story {issue_key} created. "
        f"**Next step:** Generate subtasks — run `/atlassian-pm:create-story` "
        f"subtask phase, or call `scripts/ai/suggest_subtasks.py --key {issue_key}` "
        f"to auto-generate subtask suggestions from the story's ACs."
    )


if __name__ == "__main__":
    main()
