#!/usr/bin/env python3
"""PostToolUse hook: remind to check subtask alignment after sprint data reads.

Triggers after: cache_sprint_issues, jira_get_sprint_issues, jira_get_board_issues
Suggests running sprint-subtask-alignment.py for HR8 compliance.

Exit 0 = allow (always), prints additionalContext suggestion.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_state import _load, _save

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(0)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")

# Only trigger on sprint issue reads
SPRINT_TOOLS = {
    "mcp__jira-cache-server__cache_sprint_issues",
    "mcp__mcp-atlassian__jira_get_sprint_issues",
}

if tool_name not in SPRINT_TOOLS:
    sys.exit(0)

# Extract sprint ID
sprint_id = tool_input.get("sprint_id", "")

# Debounce: only suggest once per sprint per session
state = _load(session_id)
suggested = set(state.get("alignment_suggested_sprints", []))
sprint_key = str(sprint_id)

if sprint_key in suggested:
    sys.exit(0)

suggested.add(sprint_key)
state["alignment_suggested_sprints"] = sorted(suggested)
_save(session_id, state)

print(f"📐 Sprint {sprint_id} data loaded. Run subtask alignment check:")
print(f"   python3 scripts/sprint-subtask-alignment.py --sprint {sprint_id}")
print("   Checks: HR8 dates, missing OE, parent range violations")
print("   Add --apply to fix automatically")

sys.exit(0)
