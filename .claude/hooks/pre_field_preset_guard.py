#!/usr/bin/env python3
"""PreToolUse guard: blocks jira_get_issue without `fields` and jira_search without `fields`+`limit`.

Prevents wasteful full-field fetches that consume unnecessary tokens.
Suggests presets from CLAUDE.md field tables.

Exit 2 = block with message, Exit 0 = allow.
"""

import json
import sys

PRESETS_GET = """
⚠️ BLOCKED: `fields` param is required for jira_get_issue (saves tokens).

**Presets (pick one):**
| Use Case | fields |
|----------|--------|
| Quick check | `summary,status,assignee` |
| Read description | `summary,status,description` |
| Full analysis | `summary,status,description,issuetype,parent,labels` |
| Parent check | `parent` |
| Sprint planning | `summary,status,assignee,issuetype,priority` |
"""

PRESETS_SEARCH = """
⚠️ BLOCKED: `fields` and `limit` params are required for jira_search (saves tokens).

**Presets (pick one):**
| Use Case | fields | limit |
|----------|--------|-------|
| Sprint overview | `summary,status,assignee,issuetype,priority` | 30 |
| Sub-task list | `summary,status,assignee` | 20 |
| Search duplicates | `summary,status,issuetype` | 10 |
| Full with links | `summary,status,assignee,issuetype,issuelinks,priority,labels` | 20 |
"""

raw = sys.stdin.read()
data = json.loads(raw)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

if tool_name.endswith("jira_get_issue"):
    if not tool_input.get("fields"):
        print(PRESETS_GET.strip())
        sys.exit(2)

elif tool_name.endswith("jira_search"):
    missing = []
    if not tool_input.get("fields"):
        missing.append("fields")
    if not tool_input.get("limit") and tool_input.get("limit") != 0:
        missing.append("limit")
    if missing:
        print(PRESETS_SEARCH.strip())
        sys.exit(2)

sys.exit(0)
