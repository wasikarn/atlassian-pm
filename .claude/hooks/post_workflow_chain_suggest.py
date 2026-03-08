#!/usr/bin/env python3
"""PostToolUse hook: after MCP jira_create_issue, suggest next workflow step.

Detects issue type from creation and suggests the appropriate next command.
Exit 0 = allow (always), prints additionalContext suggestion.
"""

import json
import re
import sys

raw = sys.stdin.read()
data = json.loads(raw)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
tool_output = data.get("tool_output", "")

# Only trigger on jira_create_issue
if "jira_create_issue" not in tool_name:
    sys.exit(0)

# Extract the created issue key from output
key_match = re.search(r"([A-Z]+-\d+)", str(tool_output))
if not key_match:
    sys.exit(0)

issue_key = key_match.group(1)
issue_type = tool_input.get("issue_type", "").lower()

# Suggest next step based on issue type
suggestions = {
    "epic": f"→ Next: `/create-story` under {issue_key}",
    "story": f"→ Next: `/analyze-story {issue_key}` or `/story-full` (if story just created)",
    "task": f"→ Next: `/verify-issue {issue_key}`",
}

suggestion = suggestions.get(issue_type)
if suggestion:
    print(f"💡 Created {issue_key} ({issue_type}). {suggestion}")

sys.exit(0)
