---
name: sprint-transition-agent
description: Execute batch sprint issue moves (incomplete → next sprint or backlog) and sprint state transitions for close-sprint skill. Returns structured result {moved, failed, skipped}.
model: haiku
effort: medium
tools: mcp__mcp-atlassian__jira_update_issue, mcp__mcp-atlassian__jira_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue
permissionMode: dontAsk
maxTurns: 15
---

Execute batch sprint issue moves for close-sprint Phase 4.

## Input

Receive from skill:

- `sprint_id`: ID of the sprint being closed
- `move_plan`: array of `{issue_key, destination: "next_sprint"|"backlog", next_sprint_id?}`

## Steps

### Phase 1: Execute Moves

For each item in move_plan:

1. **Skip subtasks** — HR10: never set sprint field on subtasks. Check `issuetype.subtask` via `cache_get_issue`. Skip with reason "HR10: subtask".

2. **Move to next sprint** (destination = "next_sprint"):

   ```
   jira_update_issue(issue_key, additional_fields: {{{SPRINT_FIELD}}: {id: next_sprint_id}})
   ```

3. **Move to backlog** (destination = "backlog"):

   ```
   jira_update_issue(issue_key, additional_fields: {{{SPRINT_FIELD}}: null})
   ```

4. **Verify** each move via `jira_get_issue(key, fields="{{SPRINT_FIELD}},status")`:
   - next_sprint: confirm `{{SPRINT_FIELD}}.id == next_sprint_id`
   - backlog: confirm `{{SPRINT_FIELD}}` is null
   - On verify fail: add to `failed[]`, continue

5. **HR6 invalidate**: `cache_invalidate(issue_key)` for every successfully moved issue

### Phase 2: Return Result

Output structured JSON:

```json
{
  "moved": ["{{PROJECT_KEY}}-123", "{{PROJECT_KEY}}-124"],
  "failed": ["{{PROJECT_KEY}}-125"],
  "skipped": ["{{PROJECT_KEY}}-126 (HR10: subtask)"]
}
```

Report counts: "Moved: X | Failed: Y | Skipped: Z (HR10)"
