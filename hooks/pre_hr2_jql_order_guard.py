#!/usr/bin/env python3
"""HR2: Block JQL with parent= AND ORDER BY.

PreToolUse hook for jira_search.
JQL parser errors when ORDER BY is combined with parent= or parent in (...).

Exit codes: 0 = allow, 2 = deny
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import log_event

_HOOK = "hr2-jql-order-by-guard"

PARENT_RE = re.compile(r"\bparent\s*(?:=|in\b)", re.I)
ORDER_BY_RE = re.compile(r"\bORDER\s+BY\b", re.I)


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    tool_input = data.get("tool_input", {})
    jql = tool_input.get("jql", "") or tool_input.get("query", "")

    if not jql:
        print("{}")
        return

    has_parent = bool(PARENT_RE.search(jql))
    has_order_by = bool(ORDER_BY_RE.search(jql))

    if has_parent and has_order_by:
        reason = (
            f"HR2 BLOCKED: JQL contains 'parent' AND 'ORDER BY' — parser error.\n"
            f"Remove ORDER BY when using parent= or parent in (...).\n"
            f"JQL: {jql[:200]}"
        )
        log_event(_HOOK, "BLOCKED", {"jql": jql[:500], "session_id": data.get("session_id", "")})
        print(reason, file=sys.stderr)
        sys.exit(2)

    log_event(_HOOK, "ALLOWED", {"session_id": data.get("session_id", "")})
    print("{}")


if __name__ == "__main__":
    main()
