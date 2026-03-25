#!/usr/bin/env python3
"""Auto-trigger replenishment check when an item moves to Done.

PostToolUse hook for mcp__mcp-atlassian__jira_transition_issue.
Reads tool_input.transition (the requested transition name — reliable for PostToolUse
since the hook only fires on successful tool calls).
Injects an imperative instruction so Claude runs /flow-check --replenish.

Exit codes: always 0 (inject_context or pass through silently)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin

_HOOK = "scrumban-done-trigger"
_DONE_KEYWORDS = frozenset([
    "done", "close", "closed", "complete", "completed",
    "resolve", "resolved", "finish", "finished",
])


def is_done_transition(transition: str) -> bool:
    """Return True if transition name indicates moving to a Done-equivalent state."""
    if not transition:
        return False
    t = transition.lower().strip()
    return any(kw in t for kw in _DONE_KEYWORDS)


def build_replenish_instruction(issue_key: str) -> str:
    """Build the imperative instruction Claude acts on."""
    return (
        f"Item {issue_key} moved to Done. "
        f"Now run /flow-check --replenish to check the Ready queue and trigger replenishment if needed."
    )


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    transition = str(tool_input.get("transition", tool_input.get("transition_id", ""))).strip()
    issue_key = str(tool_input.get("issue_key", tool_input.get("issue_key_or_id", ""))).upper()

    if not is_done_transition(transition):
        allow()
        return

    log_event(_HOOK, "TRIGGERED", {"issue_key": issue_key, "transition": transition})
    inject_context(build_replenish_instruction(issue_key))


if __name__ == "__main__":
    main()
