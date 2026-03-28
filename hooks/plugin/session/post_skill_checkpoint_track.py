#!/usr/bin/env python3
"""Track created issue keys as skill checkpoints — survive context compaction.

PostToolUse hook for jira_create_issue and jira_batch_create_issues.
Saves each created key + type to skill_checkpoints in session state so
start_compact_reinject.py can restore "what was already created" context
after compaction, without requiring any skill re-execution.

Exit codes: 0 (always — PostToolUse cannot block)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, log_event, parse_stdin
from hooks_state import skill_checkpoint_save

_HOOK = "skill-checkpoint-track"


def _extract_issue_type(tool_input: dict) -> str:
    """Extract issue type from create tool_input."""
    additional = tool_input.get("additional_fields", {})
    if isinstance(additional, str):
        try:
            additional = json.loads(additional)
        except (json.JSONDecodeError, TypeError):
            additional = {}
    issuetype = additional.get("issuetype", {})
    if isinstance(issuetype, dict):
        return issuetype.get("name", "Story")
    if isinstance(issuetype, str):
        return issuetype
    return tool_input.get("issue_type", "Story")


def _extract_parent_key(tool_input: dict) -> str | None:
    """Extract parent key from create tool_input.additional_fields."""
    additional = tool_input.get("additional_fields", {})
    if isinstance(additional, str):
        try:
            additional = json.loads(additional)
        except (json.JSONDecodeError, TypeError):
            additional = {}
    parent = additional.get("parent")
    if isinstance(parent, dict):
        return parent.get("key") or parent.get("id")
    if isinstance(parent, str):
        return parent
    return None


def _parse_response_key(response) -> str | None:
    """Extract created issue key from tool_response."""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return None
    if isinstance(response, dict):
        return response.get("key")
    return None


def _parse_batch_keys(response) -> list[str]:
    """Extract created issue keys from jira_batch_create_issues response."""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(response, list):
        return [item["key"] for item in response if isinstance(item, dict) and item.get("key")]
    if isinstance(response, dict):
        issues = response.get("issues", [])
        return [item["key"] for item in issues if isinstance(item, dict) and item.get("key")]
    return []


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    session_id = data.get("session_id", "")
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})

    issue_type = _extract_issue_type(tool_input)
    parent_key = _extract_parent_key(tool_input)

    if tool_name == "mcp__mcp-atlassian__jira_create_issue":
        key = _parse_response_key(tool_response)
        if key:
            try:
                skill_checkpoint_save(session_id, key, issue_type, parent_key)
                log_event(_HOOK, "TRACKED", {"key": key, "type": issue_type, "parent": parent_key})
            except Exception as e:
                log_event(_HOOK, "ERROR", {"key": key, "error": str(e)})

    elif tool_name == "mcp__mcp-atlassian__jira_batch_create_issues":
        keys = _parse_batch_keys(tool_response)
        for key in keys:
            try:
                skill_checkpoint_save(session_id, key, issue_type, parent_key)
            except Exception as e:
                log_event(_HOOK, "ERROR", {"key": key, "error": str(e)})
        if keys:
            log_event(_HOOK, "TRACKED", {"keys": keys, "type": issue_type, "count": len(keys)})

    allow()


if __name__ == "__main__":
    main()
