#!/usr/bin/env python3
"""PreToolUse hook: warn before activating a sprint without risk assessment.

Fires on jira_update_sprint when state is being set to 'active'.
Injects a reminder to run /atlassian-pm:apm-risk-forecaster before starting the sprint.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import parse_stdin, inject_context

try:
    from hooks_state import risk_is_sprint_assessed
    _HAS_STATE = True
except ImportError:
    _HAS_STATE = False


def main():
    data = parse_stdin()
    if not data:
        return

    tool_input = data.get("tool_input", {})

    # Only care about activating sprints
    new_state = tool_input.get("state", "").lower()
    if new_state != "active":
        return

    sprint_id = tool_input.get("sprintId") or tool_input.get("sprint_id", "unknown")

    # Check if risk was already assessed this session
    if _HAS_STATE:
        session_id = data.get("session_id", "")
        if risk_is_sprint_assessed(session_id, str(sprint_id)):
            return  # Already assessed, don't nag

    inject_context(
        f"**Sprint Risk Check:** Sprint {sprint_id} is being activated. "
        f"Consider running `/atlassian-pm:apm-risk-forecaster` first to assess delivery risk "
        f"(capacity, complexity hotspots, dependency chains) before committing the team. "
        f"To suppress this reminder, run risk-forecaster — it will mark the sprint as assessed.",
        event_name="PreToolUse",
    )


if __name__ == "__main__":
    main()
