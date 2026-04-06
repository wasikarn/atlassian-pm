---
name: apm-retro-actions
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

# /atlassian-pm:apm-retro-actions

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

If `--from-page` flag: `confluence_get_page(page_id)` → extract fenced `action-items` JSON block → parse → `action_items[]`, derive `sprint_label` from page title (e.g., `retro-sprint-47`).

Else: scan session context for most recent `action-items` fenced block → parse → `action_items[]`, derive `sprint_label` from context.

If `--sprint` flag: use that sprint's name as `sprint_label` (overrides derived value).

Validate: each item must have `title`, `description`, `priority`, `type`. Reject malformed entries with warning. Display: "Found N action items from [source]".

If neither source available: STOP and ask user to provide a Confluence page ID or run `/retrospective-analyst` first.

## Phase 2 — Deduplicate

HR2 — JQL with `key in (...)` MUST NOT include `ORDER BY`.

For each action item, search: `project = "{{PROJECT_KEY}}" AND issuetype = Task AND summary ~ "[Retro]" AND summary ~ "<first 40 chars>" AND created >= -30d`

- Match found → skip, note: "Skipping '[title]' — similar task exists: KEY"
- No match → include in `new_items[]`

Display: `Deduplication: N new items to create, M skipped (already exist)`

If `--dry-run`: STOP, display `new_items[]` preview table and exit.

## Phase 3 — Create Tasks

HR1 — verify ADF before writing. HR6 — no cache invalidation needed for new issues.

For each item in `new_items[]`:

1. Build ADF description with info panel (`item.description`) + paragraph (`Type`, `Priority`, `Suggested Owner`, `Sprint Target` fields).

2. `jira_create_issue(projectKey, summary="[Retro] <sprint_label>: <item.title>", issuetype="Task", priority=<mapped>, labels=["<sprint_label>", "retro-action"], description=<ADF>)`

3. If `--from-page`: `jira_add_comment(issue_key, "Created from retrospective action items. Source: [page title](url)")`

4. Append `issue_key` to `created_keys[]`

> **🟡 REVIEW** — After creating each task, display key + summary. Proceed unless user objects.

## Phase 4 — Summary

Display table of created tasks:

```
## Retro Action Items — Created

| # | Key | Title | Priority | Type | Assignee Hint |
|---|-----|-------|----------|------|---------------|
...

Total: N tasks created, M skipped (duplicates)

Next steps:
- Assign owners: /atlassian-pm:assign-issue <KEY> <name>
- Add to next sprint: move issues to sprint in Jira board
- Review: /atlassian-pm:verify-issue <KEY>
```

## Examples

```text
/retro-actions                                   # parse action-items block from session context
/retro-actions --from-page 12345678              # from Confluence retro page ID
/retro-actions --from-page 12345678 --dry-run    # preview only — no Jira writes
/retro-actions --sprint 47                       # override sprint label
```

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)

## References

[Sprint Frameworks](../../../references/sprint-frameworks.md) · [Skill Orchestration](../../../references/skill-orchestration.md) · [Templates Core](../../../references/templates-core.md) · [HR Rules](../../../references/hr-rules.md)
