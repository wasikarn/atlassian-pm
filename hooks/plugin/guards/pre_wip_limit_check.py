#!/usr/bin/env python3
"""Hard WIP gate: block jira_transition_issue when target column needs WIP check.

PreToolUse hook for mcp__mcp-atlassian__jira_transition_issue.
Uses same DoR/DoD pattern: block() + env var bypass after Claude verifies count.

Pattern:
  1. Detect target column from transition name
  2. block() with JQL + confirmation instruction
  3. Claude runs jira_search, counts WIP
  4. If WIP < limit: Claude sets CLAUDE_WIP_CONFIRMED=<key>:<col>, retries
  5. Hook reads env var — allows if confirmed

Exit codes: 0 (allow via allow()) | 2 (block via block())
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, block, log_event, parse_stdin

_HOOK = "wip-hard-gate"
_MAX_DISPLAY_KEYS = 5


def _load_config() -> dict:
    try:
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        config_path = Path(plugin_root) / ".claude" / "project-config.json"
        return json.loads(config_path.read_text())
    except Exception:
        return {}


def find_column(transition: str, columns: dict) -> tuple[str | None, dict | None]:
    """Find column name and config for a given transition/status name.

    Case-insensitive match against each column's statuses list.
    Returns (column_name, config) or (None, None) if not found.
    """
    if not transition:
        return None, None
    t_lower = transition.lower()
    for col_name, cfg in columns.items():
        for status in cfg.get("statuses", []):
            if status.lower() == t_lower:
                return col_name, cfg
    return None, None


def build_block_message(
    issue_key: str,
    col_name: str,
    wip_max: int,
    current_keys: list[str],
    jql: str,
) -> str:
    """Build the block reason shown to Claude. Instructs count check + confirmation."""
    display = current_keys[:_MAX_DISPLAY_KEYS]
    suffix = " ..." if len(current_keys) > _MAX_DISPLAY_KEYS else ""
    keys_str = ", ".join(display) + suffix if display else "(none yet)"
    return (
        f"⛔ HR-WIP: Confirm WIP count before moving {issue_key} to '{col_name}' (limit: {wip_max}).\n\n"
        f"Run: jira_search(jql=\"{jql}\", fields=\"summary,key\", max_results=50)\n"
        f"Count the results.\n"
        f"  • If count < {wip_max}: set CLAUDE_WIP_CONFIRMED={issue_key}:{col_name} then retry.\n"
        f"  • If count >= {wip_max}: Do NOT proceed. Finish or move an existing item first.\n\n"
        f"Known items in '{col_name}': {keys_str}"
    )


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    issue_key = str(tool_input.get("issue_key", tool_input.get("issue_key_or_id", ""))).upper()
    transition = str(tool_input.get("transition", tool_input.get("transition_id", ""))).strip()

    if not transition:
        allow()
        return

    cfg = _load_config()
    columns = cfg.get("board", {}).get("columns", {})
    if not columns:
        log_event(_HOOK, "SKIP", {"reason": "no_board_config"})
        allow()
        return

    col_name, col_cfg = find_column(transition, columns)
    if col_name is None:
        allow()
        return

    wip_max = col_cfg.get("wip_max")
    if not wip_max:
        allow()
        return

    # Check env var bypass — Claude sets this after confirming WIP is below limit
    confirm_key = f"{issue_key}:{col_name}"
    if os.environ.get("CLAUDE_WIP_CONFIRMED", "") == confirm_key:
        log_event(_HOOK, "ALLOWED", {"issue_key": issue_key, "col": col_name, "confirmed": True})
        allow()
        return

    # Build JQL for Claude to run the count check
    project_key = cfg.get("jira", {}).get("project_key", "")
    statuses_quoted = ", ".join(f'"{s}"' for s in col_cfg.get("statuses", []))
    jql = f'project = "{project_key}" AND status IN ({statuses_quoted})'

    log_event(_HOOK, "BLOCKED", {"issue_key": issue_key, "col": col_name, "wip_max": wip_max})
    block(build_block_message(issue_key, col_name, wip_max, [], jql))


if __name__ == "__main__":
    main()
