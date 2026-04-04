#!/usr/bin/env python3
"""Consolidated cache optimization hook for jira_get_issue, jira_search, and cache_get_issue.

Combines 4 previous hooks into one to reduce process spawn overhead:
1. Field preset injection (was pre_field_preset_guard.py)
2. Cache preference blocking (was pre_cache_prefer.py)
3. Cache-first warnings (was pre_cache_first_warning.py)
4. Stale read blocking (was pre_hr6_stale_read_guard.py)

Behaviour by tool:
  jira_get_issue:
    - Inject fields param if missing (token efficiency)
    - Block if cache not tried first (cache_is_checked)
    - Warn if cache preferred (up to 3/session)
  jira_search:
    - Inject fields + limit params if missing
    - Warn if cache preferred (up to 3/session)
  jira_get_sprint_issues:
    - Warn if cache preferred (up to 3/session)
  cache_get_issue:
    - Block if stale read (pending invalidation)

Exit codes: 0 = allow (pass), 1 = block (deny), 2 = runtime error
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import (
    allow,
    block,
    get_issue_key,
    inject_context,
    log_event,
    parse_stdin,
    update_tool_input,
)
from hooks_state import (
    cache_is_checked,
    cache_warning_count,
    cache_warning_increment,
    hr6_get_pending,
)

_HOOK = "cache-optimize"

# Field presets for token efficiency
DEFAULT_GET_FIELDS = "summary,status,description,issuetype,parent,labels,assignee,priority"
DEFAULT_SEARCH_FIELDS = "summary,status,assignee,issuetype,priority"
DEFAULT_SEARCH_LIMIT = 30

# Tool mapping: base MCP -> cache equivalent
TOOL_SUGGESTIONS = {
    "jira_get_issue": "cache_get_issue",
    "jira_search": "cache_search",
    "jira_get_sprint_issues": "cache_sprint_issues",
}


def _matches_tool(tool_name: str, patterns: str) -> bool:
    """Check if tool_name matches any pattern (pipe-separated)."""
    return any(p in tool_name for p in patterns.split("|"))


def _handle_field_preset(data: dict) -> tuple[dict | None, str | None]:
    """Inject default fields/limit if missing. Returns (new_input, context) or (None, None)."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if _matches_tool(tool_name, "jira_get_issue"):
        if not tool_input.get("fields"):
            new_input = {**tool_input, "fields": DEFAULT_GET_FIELDS}
            return new_input, f"Auto-injected fields='{DEFAULT_GET_FIELDS}' (no fields param -> token-safe default)."

    elif _matches_tool(tool_name, "jira_search"):
        injected = []
        new_input = dict(tool_input)

        if not new_input.get("fields"):
            new_input["fields"] = DEFAULT_SEARCH_FIELDS
            injected.append(f"fields='{DEFAULT_SEARCH_FIELDS}'")

        if not new_input.get("limit") and new_input.get("limit") != 0:
            new_input["limit"] = DEFAULT_SEARCH_LIMIT
            injected.append(f"limit={DEFAULT_SEARCH_LIMIT}")

        if injected:
            return new_input, f"Auto-injected {', '.join(injected)} (token-safe defaults)."

    return None, None


def _handle_cache_prefer(data: dict, session_id: str) -> tuple[bool, str | None]:
    """Block jira_get_issue if cache not tried first. Returns (should_block, reason)."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only applies to jira_get_issue
    if not _matches_tool(tool_name, "jira_get_issue"):
        return False, None

    # Skip if user explicitly opts out
    if tool_input.get("force_refresh") is True or tool_input.get("use_cache") is False:
        return False, None

    issue_key = get_issue_key(tool_input)
    if not issue_key:
        return False, None

    # Check if cache was already tried for this issue
    if cache_is_checked(session_id, issue_key):
        # Cache was tried - allow MCP fallback
        return False, None

    # Cache NOT tried - block and suggest
    return True, (
        f"CACHE-FIRST: Try cache_get_issue(issue_key='{issue_key}') before "
        f"calling jira_get_issue. If cache miss, retry jira_get_issue.\n"
        f"Reason: Local cache is faster and reduces Jira API load."
    )


def _handle_cache_warning(data: dict, session_id: str) -> tuple[bool, str | None]:
    """Emit cache-first warning (non-blocking). Returns (should_warn, message)."""
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Find matching tool
    matched_tool = None
    for base_tool in TOOL_SUGGESTIONS:
        if base_tool in tool_name:
            matched_tool = base_tool
            break

    if not matched_tool:
        return False, None

    # Skip warning if user explicitly opts out
    if tool_input.get("force_refresh") is True:
        return False, None

    if tool_input.get("use_cache") is False:
        return False, None

    # Check warning count - stop after 3 to avoid spam
    count = cache_warning_count(session_id)
    if count >= 3:
        return False, None

    # Increment warning count
    cache_warning_increment(session_id)
    cache_tool = TOOL_SUGGESTIONS[matched_tool]

    return True, (
        f"CACHE-FIRST SUGGESTION: Consider using {cache_tool}() instead of {matched_tool}() "
        f"for 80-95% token savings. Use {cache_tool}(force_refresh=true) if you need fresh data. "
        f"(Warning {count + 1}/3 this session)"
    )


def _handle_stale_read_guard(data: dict, session_id: str) -> tuple[bool, str | None]:
    """Block cache_get_issue if stale read (pending invalidation). Returns (should_block, reason)."""
    tool_name = data.get("tool_name", "")

    # Only applies to cache_get_issue
    if not _matches_tool(tool_name, "cache_get_issue"):
        return False, None

    issue_key = get_issue_key(data.get("tool_input", {}))
    if not issue_key:
        return False, None

    pending = hr6_get_pending(session_id)
    if issue_key in pending:
        return True, (
            f"HR6 BLOCKED: Cannot read {issue_key} - cache invalidation pending.\n"
            f"Run: cache_invalidate(issue_key='{issue_key}') first, then retry."
        )

    return False, None


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "")

    # Track actions for logging
    actions_taken = []

    # ========================================
    # 1. Stale read guard (cache_get_issue only)
    # ========================================
    should_block, reason = _handle_stale_read_guard(data, session_id)
    if should_block and reason:
        log_event(_HOOK, "BLOCKED", {
            "reason": "stale_read",
            "issue_key": get_issue_key(tool_input),
            "session_id": session_id,
        })
        block(reason)
        return  # unreachable, but explicit

    # ========================================
    # 2. Cache preference blocking (jira_get_issue only)
    # ========================================
    should_block, reason = _handle_cache_prefer(data, session_id)
    if should_block and reason:
        log_event(_HOOK, "BLOCKED", {
            "reason": "cache_prefer",
            "issue_key": get_issue_key(tool_input),
            "session_id": session_id,
        })
        block(reason)
        return

    # ========================================
    # 3. Field preset injection (jira_get_issue, jira_search)
    # ========================================
    new_input, context = _handle_field_preset(data)
    if new_input:
        log_event(_HOOK, "AUTO_FIXED", {
            "action": "field_preset",
            "tool": tool_name.split("__")[-1],
            "session_id": session_id,
        })
        actions_taken.append("field_preset")
        # If we have both new input and need to warn, update input with context
        # Otherwise just update input

    # ========================================
    # 4. Cache-first warning (non-blocking)
    # ========================================
    should_warn, message = _handle_cache_warning(data, session_id)
    if should_warn:
        log_event(_HOOK, "WARN", {
            "action": "cache_warning",
            "tool": tool_name.split("__")[-1],
            "session_id": session_id,
        })
        actions_taken.append("cache_warning")

    # ========================================
    # Output decision
    # ========================================
    if new_input:
        # We have field injection - update tool input
        # Combine field preset context with warning if any
        full_context = context
        if should_warn and message:
            full_context = f"{context}\n{message}" if context else message
        update_tool_input(new_input, context=full_context if full_context else None)
        sys.exit(0)
    elif should_warn and message:
        # No field injection, but we have a warning - inject context only
        inject_context(message, event_name="PreToolUse")
        sys.exit(0)
    else:
        # No actions needed - allow silently
        allow()


if __name__ == "__main__":
    main()