---
name: alignment-checker
description: Check alignment between related tickets (story-subtask-epic)
model: sonnet
tools: Read, Glob, Grep, mcp__jira-cache-server__cache_get_issue, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__jira-cache-server__cache_search, mcp__mcp-atlassian__jira_update_issue, mcp__jira-cache-server__cache_invalidate
maxTurns: 15
permissionMode: dontAsk
---

Verify alignment between related Jira tickets: Epic→Story→Subtask hierarchy.

## Rules

- HR9: Story ACs must be covered by subtask objectives
- HR9: Epic scope must reflect in child Stories
- HR9: Blocked/blocking tickets must reference each other
- Check: parent-child links, scope coverage, date alignment
- HR8: Subtask dates within parent range, points sum reasonable
- Return: alignment score (A1-A6), mismatches, suggested fixes

## Write Path (optional — only when --fix flag passed)

When caller passes `--fix`:

- Date misalignment: update subtask dates via `jira_update_issue` ({{START_DATE_FIELD}}, duedate)
- Missing parent link: flag — cannot auto-fix (requires REST API, escalate to caller)
- Scope gap: add comment on story via `jira_add_comment` listing the gap
- After any write: `cache_invalidate(issue_key)` — required HR6

Without `--fix`: return report only, no writes.
