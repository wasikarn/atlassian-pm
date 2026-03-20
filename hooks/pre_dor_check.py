#!/usr/bin/env python3
"""DoR enforcement: block jira_transition_issue when moving to In Progress without DoR check.

PreToolUse hook for mcp__mcp-atlassian__jira_transition_issue.
Symmetric with pre_dod_check.py (Done gate). This gate fires at the other end.

Confirmation signal: CLAUDE_DOR_CONFIRMED=<issue_key> (set by Claude after manual check).
Exit codes: 0 = allow (prints {}), 2 = block (prints reason to stderr)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import allow, block, log_event, parse_stdin

_HOOK = "dor-gate"

_IN_PROGRESS_KEYWORDS = [
    "in progress", "in development", "start", "doing", "active",
    "in-progress", "inprogress",
]


def _is_in_progress(transition: str) -> bool:
    t = transition.lower()
    return any(kw in t for kw in _IN_PROGRESS_KEYWORDS)


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    issue_key = str(tool_input.get("issue_key", "")).upper()
    transition = str(tool_input.get("transition", tool_input.get("transition_id", "")))

    if not _is_in_progress(transition):
        allow()
        return

    confirmed = os.environ.get("CLAUDE_DOR_CONFIRMED", "").upper()
    if confirmed == issue_key:
        log_event(_HOOK, "ALLOWED", {"issue_key": issue_key})
        allow()
        return

    log_event(_HOOK, "BLOCKED", {"issue_key": issue_key, "transition": transition})
    block(
        f"⛔ DoR Check required before moving {issue_key} to '{transition}'.\n\n"
        "Verify ALL of the following:\n"
        "  1. Story has at least 1 subtask created and linked\n"
        "  2. Story has Acceptance Criteria in the description\n"
        "  3. Story passed Quality Gate ≥ 90% (run /verify-issue if unsure)\n\n"
        f"When all checks pass → set CLAUDE_DOR_CONFIRMED={issue_key} and retry.\n"
        "To add subtasks: /analyze-story   To verify quality: /verify-issue"
    )


if __name__ == "__main__":
    main()
