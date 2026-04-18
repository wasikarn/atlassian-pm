#!/usr/bin/env python3
"""PostToolUse: Remind agent to fix code blocks after confluence_update_page.

Trigger: PostToolUse event where tool_name == "confluence_update_page" (MCP tool).

The MCP confluence_update_page tool may silently flatten code blocks or
break panels/macros on update. This hook injects a reminder with the
exact command to verify and auto-fix after every successful Confluence write.

Silent exit 0 on non-matching tools or any error.
Exit codes: always 0 — PostToolUse hooks cannot block.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
from hooks_lib import allow, inject_context, parse_stdin  # noqa: E402

_TOOL_NAME = "confluence_update_page"

_NOTE_TEMPLATE = (
    "NOTE: `confluence_update_page` MCP may have flattened code blocks or broken "
    "panels/macros. Run `python3 scripts/api/fix_confluence_code_blocks.py "
    "--page-id {page_id}` to verify and auto-fix. "
    "Also consider `fix_confluence_panels.py` if panels were used."
)


def _extract_page_id(data: dict) -> str:
    """Extract page_id from tool_input, with fallback to common field names."""
    tool_input = data.get("tool_input") or {}
    if isinstance(tool_input, str):
        import json
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    for field in ("page_id", "id", "pageId"):
        val = tool_input.get(field)
        if val:
            return str(val)
    return "<page_id>"


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_name = data.get("tool_name", "")
    if tool_name != _TOOL_NAME:
        allow()
        return

    page_id = _extract_page_id(data)
    inject_context(
        _NOTE_TEMPLATE.format(page_id=page_id),
        event_name="PostToolUse",
    )


if __name__ == "__main__":
    main()
