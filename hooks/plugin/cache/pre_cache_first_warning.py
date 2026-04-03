#!/usr/bin/env python3
"""PreToolUse warning: suggest cache_* tools over base MCP for read operations.

Non-blocking hook that warns when base MCP tools are used instead of cache equivalents.
Tracks warning count per session to avoid spamming after 3 warnings.

Behaviour:
  - jira_get_issue      → suggest cache_get_issue (80-95% token savings)
  - jira_search         → suggest cache_search (80-95% token savings)
  - jira_get_sprint_issues → suggest cache_sprint_issues (80-95% token savings)

Exceptions (don't warn):
  - force_refresh=true  → user explicitly wants fresh data
  - use_cache=false     → explicit opt-out of cache

Exit 0 = allow (always — warning only, never blocks)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import inject_context, log_event, parse_stdin
from hooks_state import cache_warning_count, cache_warning_increment

_HOOK = "cache-first-warning"

# Tool mapping: base MCP → cache equivalent
TOOL_SUGGESTIONS = {
    "jira_get_issue": "cache_get_issue",
    "jira_search": "cache_search",
    "jira_get_sprint_issues": "cache_sprint_issues",
}


def main() -> None:
    data = parse_stdin()
    if not data:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "")

    # Only target specific base MCP tools
    matched_tool = None
    for base_tool in TOOL_SUGGESTIONS:
        if base_tool in tool_name:
            matched_tool = base_tool
            break

    if not matched_tool:
        sys.exit(0)

    # Skip warning if user explicitly opts out
    if tool_input.get("force_refresh") is True:
        log_event(_HOOK, "SKIP", {"reason": "force_refresh", "tool": matched_tool, "session_id": session_id})
        sys.exit(0)

    if tool_input.get("use_cache") is False:
        log_event(_HOOK, "SKIP", {"reason": "use_cache_false", "tool": matched_tool, "session_id": session_id})
        sys.exit(0)

    # Check warning count — stop after 3 to avoid spam
    count = cache_warning_count(session_id)
    if count >= 3:
        log_event(_HOOK, "SKIP", {"reason": "max_warnings_reached", "count": count, "tool": matched_tool, "session_id": session_id})
        sys.exit(0)

    # Increment warning count
    cache_warning_increment(session_id)
    cache_tool = TOOL_SUGGESTIONS[matched_tool]

    # Log the warning
    log_event(_HOOK, "WARN", {
        "tool": matched_tool,
        "suggested": cache_tool,
        "session_id": session_id,
        "warning_count": count + 1,
    })

    # Inject context warning (non-blocking)
    inject_context(
        f"CACHE-FIRST SUGGESTION: Consider using {cache_tool}() instead of {matched_tool}() "
        f"for 80-95% token savings. Use {cache_tool}(force_refresh=true) if you need fresh data. "
        f"(Warning {count + 1}/3 this session)",
        event_name="PreToolUse",
    )

    sys.exit(0)


if __name__ == "__main__":
    main()