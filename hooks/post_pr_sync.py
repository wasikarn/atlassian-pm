#!/usr/bin/env python3
"""PR sync: inject Jira transition context after gh pr create.

PostToolUse hook for Bash.
When Claude runs 'gh pr create', extracts BEP-XXX from the command or output
and injects additionalContext telling Claude to transition the issue to In Review.

Exit codes: always 0 (PostToolUse cannot block)
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context, log_event, parse_stdin

_HOOK = "pr-sync"
_ISSUE_RE = re.compile(r'\b(BEP-\d+)\b', re.IGNORECASE)


def _find_issue_key(command: str, response: str) -> str | None:
    for text in (command, response):
        m = _ISSUE_RE.search(text)
        if m:
            return m.group(1).upper()
    return None


def main() -> None:
    data = parse_stdin()
    if not data:
        print("{}")
        return

    command = data.get("tool_input", {}).get("command", "")
    if "gh pr create" not in command:
        print("{}")
        return

    response = data.get("tool_response", "")
    if isinstance(response, dict):
        response = json.dumps(response)

    issue_key = _find_issue_key(command, str(response))
    if not issue_key:
        log_event(_HOOK, "SKIP", {"reason": "no_bep_key", "cmd": command[:80]})
        print("{}")
        return

    log_event(_HOOK, "INJECT", {"issue_key": issue_key})
    inject_context(
        f"PR created — transition {issue_key} to 'In Review': "
        f"jira_transition_issue(issue_key='{issue_key}', transition='In Review'). "
        f"Then cache_invalidate(issue_key='{issue_key}') per HR6."
    )


if __name__ == "__main__":
    main()
