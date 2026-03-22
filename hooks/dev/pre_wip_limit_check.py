#!/usr/bin/env python3
"""WIP limit soft-guard: inject context to check assignee WIP before moving to In Progress.

PreToolUse hook for mcp__mcp-atlassian__jira_transition_issue.
Fires when transitioning to "In Progress". Injects a reminder for Claude to verify
the assignee's current WIP count against the team limit from project-config.json.

Does not block (unlike pre_dor_check.py) — this is a soft warn, not a hard gate.
Exit codes: always 0 (injects context or passes through silently)
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks_lib import allow, inject_context, is_in_progress_transition, log_event, parse_stdin

_HOOK = "wip-limit"
_DEFAULT_WIP_LIMIT = 2


def _load_config() -> dict:
    try:
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        config_path = Path(plugin_root) / ".claude" / "project-config.json"
        return json.loads(config_path.read_text())
    except Exception:
        return {}


def _get_wip_limit() -> int:
    try:
        return int(_load_config().get("team", {}).get("wip_limit", _DEFAULT_WIP_LIMIT))
    except Exception:
        return _DEFAULT_WIP_LIMIT


def _get_project_key() -> str:
    return _load_config().get("jira", {}).get("project_key", "{{PROJECT_KEY}}")


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    issue_key = str(tool_input.get("issue_key", "")).upper()
    transition = str(tool_input.get("transition", tool_input.get("transition_id", "")))

    if not is_in_progress_transition(transition):
        allow()
        return

    wip_limit = _get_wip_limit()
    project_key = _get_project_key()
    log_event(_HOOK, "REMIND", {"issue_key": issue_key, "wip_limit": wip_limit})
    inject_context(
        f"WIP check: before moving {issue_key} to '{transition}', verify the assignee's "
        f"current In Progress count is below the team limit ({wip_limit}). "
        f"Run: jira_search(jql=\"project = {project_key} AND assignee = '<email>' AND status = 'In Progress'\", "
        f"fields=\"summary,assignee,status\") to check. "
        f"If count >= {wip_limit}, warn the user before proceeding.",
        event_name="PreToolUse",
    )


if __name__ == "__main__":
    main()
