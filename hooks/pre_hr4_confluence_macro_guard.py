#!/usr/bin/env python3
"""HR4: Block MCP Confluence updates containing macros.

PreToolUse hook for confluence_update_page.
MCP HTML-escapes <ac:structured-macro> tags, rendering raw XML on the page.
Macro content must use update_page_storage.py instead.

Exit codes: 0 = allow, 2 = deny
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import log_event

_HOOK = "hr4-confluence-macro-guard"

MACRO_PATTERNS = [
    re.compile(r"<ac:structured-macro", re.I),
    re.compile(r"<ac:parameter", re.I),
    re.compile(r"<ac:rich-text-body", re.I),
    re.compile(r"<ac:plain-text-body", re.I),
    re.compile(r"ac:name=", re.I),
]


def has_macros(content: str) -> bool:
    """Check if content contains Confluence macro markup."""
    return any(p.search(content) for p in MACRO_PATTERNS)


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("{}")
        return

    tool_input = data.get("tool_input", {})
    sid = data.get("session_id", "")

    # Check all string fields for macro content
    for field in ("content", "body", "value"):
        content = tool_input.get(field, "")
        if isinstance(content, str) and has_macros(content):
            page_id = tool_input.get("page_id", "?")
            log_event(_HOOK, "BLOCKED", {"page_id": str(page_id), "session_id": sid})
            reason = (
                f"HR4 BLOCKED: Confluence macro detected in MCP update for page {page_id}.\n"
                f"MCP HTML-escapes macros → page renders raw XML.\n"
                f"Use: python3 .claude/skills/atlassian-scripts/update_page_storage.py instead."
            )
            print(reason, file=sys.stderr)
            sys.exit(2)

    log_event(_HOOK, "ALLOWED", {"session_id": sid})
    print("{}")


if __name__ == "__main__":
    main()
