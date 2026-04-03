"""PostToolUse hook: log response sizes for MCP calls to track token usage patterns.

Logs response sizes for MCP tools that return large payloads (Jira, Confluence, cache).
Tracks per-session and per-tool stats in session state for cumulative analysis.

Exit 0 = always allow (observability only, never blocks).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event, parse_stdin, get_tool_response
from hooks_state import response_size_track

_HOOK = "response-size-log"

# MCP tools to track (Jira, Confluence, Cache)
TRACKED_TOOLS = {
    # Jira MCP
    "mcp__mcp-atlassian__jira_get_issue",
    "mcp__mcp-atlassian__jira_search",
    "mcp__mcp-atlassian__jira_get_sprint_issues",
    "mcp__mcp-atlassian__jira_get_project_issues",
    "mcp__mcp-atlassian__jira_get_board_issues",
    "mcp__mcp-atlassian__jira_get_agile_boards",
    "mcp__mcp-atlassian__jira_get_sprints_from_board",
    "mcp__mcp-atlassian__jira_get_transitions",
    "mcp__mcp-atlassian__jira_get_issue_links",
    "mcp__mcp-atlassian__jira_get_worklog",
    "mcp__mcp-atlassian__jira_batch_get_changelogs",
    # Confluence MCP
    "mcp__mcp-atlassian__confluence_get_page",
    "mcp__mcp-atlassian__confluence_get_page_children",
    "mcp__mcp-atlassian__confluence_get_page_history",
    "mcp__mcp-atlassian__confluence_get_page_views",
    "mcp__mcp-atlassian__confluence_get_attachments",
    "mcp__mcp-atlassian__confluence_get_comments",
    "mcp__mcp-atlassian__confluence_search",
    # Cache MCP
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue",
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issues",
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_search",
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_text_search",
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_cross_search",
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_sprint_issues",
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_similar_issues",
    "mcp__plugin_atlassian-pm_atlassian-cache__cache_stats",
}

# Short names for logging (strip mcp prefix)
TOOL_SHORT_NAMES = {
    name.replace("mcp__mcp-atlassian__", "").replace("mcp__plugin_atlassian-pm_atlassian-cache__", "cache_")
    for name in TRACKED_TOOLS
}


def _get_short_name(tool_name: str) -> str:
    """Extract short tool name for readable logs."""
    if "atlassian-cache" in tool_name:
        return tool_name.replace("mcp__plugin_atlassian-pm_atlassian-cache__", "cache_")
    return tool_name.replace("mcp__mcp-atlassian__", "")


def _estimate_tokens(char_count: int) -> int:
    """Estimate tokens from character count.

    Uses 4 chars per token as a rough approximation for English text.
    This is a conservative estimate (actual is often 3-4 chars/token).
    """
    return max(1, char_count // 4)


data = parse_stdin()
if not data:
    sys.exit(0)

tool_name = data.get("tool_name", "")
session_id = data.get("session_id", "")

# Only track configured MCP tools
if tool_name not in TRACKED_TOOLS:
    sys.exit(0)

# Extract response and calculate size
response_str = get_tool_response(data)
char_count = len(response_str)
token_estimate = _estimate_tokens(char_count)
short_name = _get_short_name(tool_name)

# Check if fields param was used (indicates token-conscious call)
tool_input = data.get("tool_input", {})
has_fields_param = "fields" in tool_input
has_limit_param = "limit" in tool_input

# Log to daily JSONL
log_event(_HOOK, "RESPONSE_SIZE", {
    "tool": short_name,
    "chars": char_count,
    "tokens_estimated": token_estimate,
    "has_fields_param": has_fields_param,
    "has_limit_param": has_limit_param,
    "session_id": session_id,
})

# Track in session state for cumulative stats
response_size_track(
    session_id=session_id,
    tool=short_name,
    chars=char_count,
    tokens=token_estimate,
)

sys.exit(0)