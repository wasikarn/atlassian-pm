---
name: retro-actions
context: fork
agent: general-purpose
effort: medium
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
argument-hint: "[--from-page <confluence-page-id>] [--sprint <sprint-id>] [--dry-run]"
description: |
  Extract action items from a retrospective and create Jira tasks.

  Reads the action-items block from a retro output (Confluence page or session context),
  creates one Jira task per action item with proper description and sprint assignment.
  Links tasks to current sprint label for traceability.

  Triggers: "retro actions", "create retro tasks", "retro to tasks", "action items from retro", "สร้าง task จาก retro"
  Use after: close-sprint or retrospective-analyst
allowed-tools: mcp__atlassian-cache__cache_get_issue, mcp__atlassian-cache__cache_search, mcp__mcp-atlassian__jira_create_issue, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__jira_add_comment, mcp__mcp-atlassian__confluence_get_page, mcp__mcp-atlassian__jira_get_sprints_from_board
---

# /retro-actions

**Role:** Scrum Master — Retrospective Action Item Executor
**Output:** Jira tasks created from retrospective action items, linked to sprint label

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Board ID:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['board_id'])"`
- **Project Key:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['project_key'])"`

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Discover | `action_items[]`, `sprint_label`, `source` (page or session) |
| 2. Deduplicate | `new_items[]` (deduplicated against existing Jira tasks) |
| 3. Create | `created_keys[]` (one Jira task key per action item) |
| 4. Summary | Table of created tasks displayed to user |

## Phase 1 — Discover Action Items

**Goal:** Locate and parse the `action-items` JSON block from the retrospective source.
**Required inputs:** `--from-page <id>` flag OR session context containing an `action-items` block
**Constraints:** If neither source is available, STOP and ask user to provide a Confluence page ID or run `/retrospective-analyst` first
**Output:** `action_items[]`, `sprint_label` available in context for Phase 2

1. If `--from-page` flag provided:
   - `confluence_get_page(page_id)` — fetch the Confluence retro page
   - Extract the fenced `action-items` block (JSON array between ` ```action-items ` and ` ``` `)
   - Parse JSON → `action_items[]`
   - Extract sprint name from page title for `sprint_label` (e.g., `retro-sprint-47`)

2. Else — read from session context:
   - Scan conversation context for the most recent `action-items` fenced block
   - Parse JSON → `action_items[]`
   - Derive `sprint_label` from sprint name if available in context (e.g., `retro-sprint-47`)

3. If `--sprint` flag provided → use that sprint's name as `sprint_label` (overrides derived value)

4. Validate parsed items:
   - Each item must have `title`, `description`, `priority`, `type`
   - Reject malformed entries and display a warning — do not silently skip
   - Display parsed count: "Found N action items from [source]"

## Phase 2 — Deduplicate

**Goal:** Avoid creating duplicate Jira tasks for action items that already exist from a prior retro run.
**Required inputs:** `action_items[]` from Phase 1
**Constraints:** HR2 — JQL with `key in (...)` MUST NOT include `ORDER BY`; search by summary prefix only
**Output:** `new_items[]` (items not already in Jira) available in context for Phase 3

For each action item title, search Jira for an existing task with a matching summary:

```jql
project = "{{PROJECT_KEY}}" AND issuetype = Task AND summary ~ "[Retro]" AND summary ~ "<first 40 chars of title>" AND created >= -30d
```

- If a match is found → skip item, note: "Skipping '[title]' — similar task exists: KEY"
- If no match → include in `new_items[]`

Display dedup summary:

```
Deduplication: N new items to create, M skipped (already exist)
```

If `--dry-run` flag provided → STOP here, display `new_items[]` preview table and exit.

## Phase 3 — Create Tasks

**Goal:** Create one Jira Task per deduplicated action item with ADF description and sprint label.
**Required inputs:** `new_items[]` from Phase 2; `sprint_label` from Phase 1
**Constraints:** HR1 — verify ADF before writing; HR6 — no cache invalidation needed (new issues have no cache entry yet)
**Output:** `created_keys[]` available in context for Phase 4

For each item in `new_items[]`:

1. Build ADF description:

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {
      "type": "panel",
      "attrs": { "panelType": "info" },
      "content": [
        {
          "type": "paragraph",
          "content": [{ "type": "text", "text": "<item.description>" }]
        }
      ]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "Type: ", "marks": [{ "type": "strong" }] },
        { "type": "text", "text": "<item.type>" },
        { "type": "hardBreak" },
        { "type": "text", "text": "Priority: ", "marks": [{ "type": "strong" }] },
        { "type": "text", "text": "<item.priority>" },
        { "type": "hardBreak" },
        { "type": "text", "text": "Suggested Owner: ", "marks": [{ "type": "strong" }] },
        { "type": "text", "text": "<item.assignee_hint or 'team'>" },
        { "type": "hardBreak" },
        { "type": "text", "text": "Sprint Target: ", "marks": [{ "type": "strong" }] },
        { "type": "text", "text": "<item.sprint_target>" }
      ]
    }
  ]
}
```

1. `jira_create_issue`:

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "summary": "[Retro] <sprint_label>: <item.title>",
  "issuetype": { "name": "Task" },
  "priority": { "name": "<High|Medium|Low — mapped from item.priority>" },
  "labels": ["<sprint_label>", "retro-action"],
  "description": "<ADF from step 1>"
}
```

1. After create → add a comment linking back to the source (if `--from-page` was used):
   `jira_add_comment(issue_key, "Created from retrospective action items. Source: [Confluence page title](url)")`

2. Append `issue_key` to `created_keys[]`

> **🟡 REVIEW** — After creating each task, display key + summary. Proceed unless user objects.

## Phase 4 — Summary

**Goal:** Present a clear summary table of all created tasks for the user to review and assign.
**Required inputs:** `created_keys[]` from Phase 3
**Constraints:** None — display only, no writes
**Output:** Summary table shown; next-step suggestions provided

Display:

```
## Retro Action Items — Created

| # | Key | Title | Priority | Type | Assignee Hint |
|---|-----|-------|----------|------|---------------|
| 1 | {{PROJECT_KEY}}-XXX | [Retro] sprint-47: ... | High | process | tech-lead |
...

Total: N tasks created, M skipped (duplicates)

Next steps:
- Assign owners: /atlassian-pm:assign-issue <KEY> <name>
- Add to next sprint: move issues to sprint in Jira board
- Review: /atlassian-pm:verify-issue <KEY>
```

## Examples

### Good

```text
/retro-actions                                   # parse action-items block from session context
/retro-actions --from-page 12345678              # from Confluence retro page ID
/retro-actions --from-page 12345678 --dry-run    # preview only — no Jira writes
/retro-actions --sprint 47                       # override sprint label
```

### Bad

```text
/retro-actions                                   # ❌ run before /retrospective-analyst — no action-items block in context
/retro-actions --from-page 12345678              # ❌ page has no action-items block — Phase 1 will fail to parse
```

**Common mistakes:**

- Running before `/retrospective-analyst` — the action-items block must exist in context or on a Confluence page
- Not verifying the `sprint_label` — a wrong label pollutes the Jira board filter for that sprint
- Skipping `--dry-run` on first run — always preview before writing to Jira on a new sprint

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
## References

[Sprint Frameworks](../../../references/sprint-frameworks.md) · [Skill Orchestration](../../../references/skill-orchestration.md) · [Templates Core](../../../references/templates-core.md) · [HR Rules](../../../references/hr-rules.md)
