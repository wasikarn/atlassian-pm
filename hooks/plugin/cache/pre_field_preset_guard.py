"""PreToolUse guard: auto-inject default fields/limit for jira_get_issue and jira_search.

Previously blocked missing params — now silently injects safe defaults via updatedInput,
preventing wasteful full-field fetches without interrupting Claude's workflow.

Behaviour:
  jira_get_issue without fields  → inject DEFAULT_GET_FIELDS
  jira_search without fields     → inject DEFAULT_SEARCH_FIELDS
  jira_search without limit      → inject DEFAULT_SEARCH_LIMIT

Exit 0 = allow (always — auto-fix replaces blocking).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event, parse_stdin, update_tool_input

_HOOK = "field-preset-guard"

DEFAULT_GET_FIELDS    = "summary,status,description,issuetype,parent,labels,assignee,priority"
DEFAULT_SEARCH_FIELDS = "summary,status,assignee,issuetype,priority"
DEFAULT_SEARCH_LIMIT  = 30

data = parse_stdin()
if not data:
    sys.exit(0)

tool_name  = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "")

if tool_name.endswith("jira_get_issue"):
    if not tool_input.get("fields"):
        new_input = {**tool_input, "fields": DEFAULT_GET_FIELDS}
        log_event(_HOOK, "AUTO_FIXED", {
            "tool": "jira_get_issue",
            "injected": "fields",
            "value": DEFAULT_GET_FIELDS,
            "session_id": session_id,
        })
        update_tool_input(
            new_input,
            context=f"Auto-injected fields='{DEFAULT_GET_FIELDS}' (no fields param → token-safe default).",
        )
        sys.exit(0)

elif tool_name.endswith("jira_search"):
    injected = []
    new_input = dict(tool_input)

    if not new_input.get("fields"):
        new_input["fields"] = DEFAULT_SEARCH_FIELDS
        injected.append(f"fields='{DEFAULT_SEARCH_FIELDS}'")

    if not new_input.get("limit") and new_input.get("limit") != 0:
        new_input["limit"] = DEFAULT_SEARCH_LIMIT
        injected.append(f"limit={DEFAULT_SEARCH_LIMIT}")

    if injected:
        log_event(_HOOK, "AUTO_FIXED", {
            "tool": "jira_search",
            "injected": injected,
            "session_id": session_id,
        })
        update_tool_input(
            new_input,
            context=f"Auto-injected {', '.join(injected)} (token-safe defaults).",
        )
        sys.exit(0)

sys.exit(0)
