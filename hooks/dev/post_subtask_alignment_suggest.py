"""PostToolUse hook: remind to check subtask alignment after sprint data reads.

Triggers after: cache_sprint_issues, jira_get_sprint_issues
Suggests running sprint-subtask-alignment.py for HR8 compliance.

Exit 0 = allow (always), injects additionalContext suggestion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks_lib import inject_context, parse_stdin
from hooks_state import alignment_is_sprint_suggested, alignment_mark_sprint_suggested

data = parse_stdin()
if not data:
    sys.exit(0)

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")

SPRINT_TOOLS = {
    "mcp__plugin_atlassian-pm_jira-cache-server__cache_sprint_issues",
    "mcp__mcp-atlassian__jira_get_sprint_issues",
}

if tool_name not in SPRINT_TOOLS:
    sys.exit(0)

sprint_id = tool_input.get("sprint_id", "")

# Debounce: only suggest once per sprint per session
if alignment_is_sprint_suggested(session_id, sprint_id):
    sys.exit(0)

alignment_mark_sprint_suggested(session_id, sprint_id)

inject_context(
    f"Sprint {sprint_id} data loaded. Run subtask alignment check:\n"
    f"   python3 scripts/sprint-subtask-alignment.py --sprint {sprint_id}\n"
    f"   Checks: HR8 dates, missing OE, parent range violations\n"
    f"   Add --apply to fix automatically"
)

sys.exit(0)
