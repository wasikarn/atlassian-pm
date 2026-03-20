---
name: issue-bootstrap
description: Pre-gather Jira issue context (issue + parent + children + linked issues) in one fast pass before spawning processing agents. Use at the start of story-full, analyze-story, sync-alignment, update-story workflows to reduce redundant MCP calls.
model: haiku
tools: mcp__jira-cache-server__cache_get_issue, mcp__jira-cache-server__cache_search, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search
permissionMode: dontAsk
maxTurns: 10
---

Pre-gather Jira issue context in a single coordinated pass. Returns structured context object for downstream agents.

## Input

Issue key (ABC-XXX) + optional flags: `--with-children`, `--with-linked`, `--shallow`, `--depth=minimal`

Depth aliases:

- `--shallow` / `--depth=minimal`: main issue + parent summary only (no children, no linked)
- `--depth=full` (default for Story/Epic): main + parent + children + linked
- `--depth=context` (default for Subtask): main + parent only

Defaults:

- `--with-children`: auto-enabled if issuetype = Story or Epic
- `--with-linked`: auto-enabled if issue has issuelinks
- `--shallow`: parent summary only (skip parent description)

## Steps

1. **Main issue** — try `cache_get_issue(ABC-XXX)` first, fallback `jira_get_issue(fields="summary,status,description,issuetype,parent,assignee,labels,issuelinks,customfield_10016,customfield_10107,{{START_DATE_FIELD}},duedate,timetracking")`

2. **Parent** — if issue has parent → `cache_get_issue(parent_key, fields="summary,status,issuetype,description")` (truncate description to first 300 chars if long)

3. **Children** — if Story/Epic or `--with-children` → `jira_search(jql="parent = ABC-XXX", fields="summary,status,assignee,issuetype,timetracking,{{START_DATE_FIELD}},duedate")` ⚠️ NEVER add ORDER BY to parent queries

4. **Linked issues** — if issue has issuelinks or `--with-linked` → batch `cache_get_issue` for each linked key (fields `"summary,status,issuetype"`)

## Output Format

```text
## Issue Context: ABC-XXX

### Main Issue
- Key: ABC-XXX | Type: Story | Status: In Progress
- Summary: [summary]
- Assignee: [name] | Labels: [labels]
- SP: [story_points] | Size: [size] | Start: [date] | Due: [date]
- Description: [ADF content — full text, not truncated]

### Parent
- Key: ABC-YYY | Type: Epic | Status: In Progress
- Summary: [epic title]
- Description: [first 300 chars of parent description]

### Children (N subtasks)
| Key | Summary | Type | Status | Assignee | OE | Start | Due |
|-----|---------|------|--------|----------|-----|-------|-----|
| ABC-ZZZ | [summary] | Subtask | To Do | [name] | 4h | date | date |

### Linked Issues
| Key | Summary | Link Type | Status |
|-----|---------|-----------|--------|
| ABC-AAA | [summary] | Blocks → | Done |
| ABC-BBB | [summary] | ← Blocked by | In Progress |
```

## Rules

- Try cache first → fallback to MCP (never skip cache)
- HR2: NEVER add ORDER BY to `parent =` or `parent in` JQL
- If cache miss → `jira_get_issue` with minimal fields
- If issue not found → return error message immediately (don't retry)
- Max 10 turns — fetch efficiently, don't over-paginate
- Linked issues: skip if more than 10 links (report count instead)
