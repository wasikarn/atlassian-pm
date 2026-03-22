#!/usr/bin/env python3
"""V: VS Integrity — Track Story ACs and Subtask coverage.

PostToolUse hook for mcp__mcp-atlassian__jira_get_issue and jira_create_issue.

When a Story is read: extracts AC titles and saves to state.
When a Subtask is created under a Story: tracks the subtask.
Prints coverage summary when gaps are detected.

Exit 0 = always allow
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import get_parent_key, get_tool_response, parse_stdin
from hooks_state import vs_add_subtask, vs_get_coverage, vs_set_story_acs

data = parse_stdin()
if not data:
    sys.exit(0)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
tool_output = get_tool_response(data)
session_id = data.get("session_id", "")

# ── Story read: extract ACs ──────────────────────────
if "jira_get_issue" in tool_name:
    # Check if this is a Story (not Epic/Subtask)
    if '"Story"' not in tool_output:
        sys.exit(0)

    key_match = re.search(r'"key"\s*:\s*"([A-Z]+-\d+)"', tool_output)
    if not key_match:
        sys.exit(0)
    story_key = key_match.group(1)

    # Extract AC titles from panel content
    # Pattern: "AC1: Verb — Scenario" or "AC1: DomainEvent — Scenario"
    ac_titles = re.findall(r"(AC\d+:\s*[^\"\\]+?)(?:\"|\\)", tool_output)
    ac_titles = [t.strip() for t in ac_titles if len(t) > 5]

    if ac_titles:
        vs_set_story_acs(session_id, story_key, ac_titles)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"📊 VS tracked {story_key}: {len(ac_titles)} ACs — "
                    f"{', '.join(ac_titles[:3])}{'...' if len(ac_titles) > 3 else ''}"
                ),
            }
        }
        print(json.dumps(output))

# ── Subtask create: track under parent ────────────────
elif "jira_create_issue" in tool_name:
    # Check if subtask (has parent)
    parent_key = get_parent_key(tool_input)

    if not parent_key:
        sys.exit(0)

    # Extract created key
    resp = data.get("tool_response", {})
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except (json.JSONDecodeError, TypeError):
            resp = {}
    child_key = resp.get("key", "UNKNOWN") if isinstance(resp, dict) else "UNKNOWN"
    summary = tool_input.get("summary", "")

    vs_add_subtask(session_id, parent_key, child_key, summary)

    # Check coverage
    coverage = vs_get_coverage(session_id)
    story_acs = coverage["story_acs"].get(parent_key, [])
    subtasks = coverage["subtasks"].get(parent_key, [])

    if story_acs and len(subtasks) >= len(story_acs):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"📊 VS coverage {parent_key}: {len(subtasks)} subtasks for "
                    f"{len(story_acs)} ACs — review coverage before proceeding."
                ),
            }
        }
        print(json.dumps(output))

sys.exit(0)
