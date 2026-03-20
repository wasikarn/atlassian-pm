---
name: retrospective-action-items
disable-model-invocation: true
x-compatibility: [jira-cache-server, mcp-atlassian, mcp-confluence, acli]
description: |
  Convert retrospective action items from a Confluence page into Jira tasks automatically.
  Reads the retrospective Confluence page, extracts action items, creates Jira Tasks linked back to the page.
  Closes the retro feedback loop that otherwise requires manual copy each sprint.
  Triggers: "retrospective action items", "retro actions", "create retro tasks", "action items from retro",
            "สร้าง task จาก retro", "action items retro"
argument-hint: "<confluence-page-id> [--sprint <id>] [--dry-run]"
---

# /retrospective-action-items

**Role:** PM — Sprint Retrospective Closure
**Output:** Jira Tasks for each action item, linked to retrospective Confluence page

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`

## Context Object

| Phase | Adds to Context |
| --- | --- |
| 1. Fetch | `page_id`, `page_title`, `page_url`, `page_content` |
| 2. Parse | `action_items[]` (text, owner, category) |
| 3. Review | `approved_items[]` |
| 4. Create | `created_tasks[]` (issue_key, summary) |
| 5. Link | Tasks linked to Confluence page |
| 6. Summary | Done |

---

## Phase 1 — Fetch Retrospective Page 🟢 AUTO

1. If `<confluence-page-id>` provided → use it directly.
2. Else → `confluence_search(query="retrospective sprint", space_key="{{SPACE_KEY}}", limit=5)` and display results for user to pick.
3. `confluence_get_page(page_id=<id>, expand="body.storage")` to fetch full content.

Display:

```
## Retrospective Page Found

**Title:** [page_title]
**URL:** [page_url]
**Last Updated:** [date]

```

---

## Phase 2 — Parse Action Items 🟡 REVIEW

Extract action items from page content. Look for:

- Sections titled "Action Items", "Actions", "Next Steps", "Improvements"
- Bullet or numbered lists within those sections
- Patterns: "→ [action]", "- [ ] [action]", "Action: [action]"

For each item extract:

| Field | Source |
| --- | --- |
| `text` | Action item description |
| `owner` | Name mentioned after "Owner:", "@name", or "ผู้รับผิดชอบ:" |
| `category` | Parent section heading (Process / Tech / Team / Communication) |

Display parsed list for review:

```
## Parsed Action Items ([N] found)

| # | Action | Owner | Category |
|---|--------|-------|----------|
| 1 | [text] | [owner or Unassigned] | [category] |
| 2 | ...    | ...   | ...      |

Any items to add, remove, or edit before creating tasks?

```

🟡 REVIEW — user can confirm or adjust before proceeding.

---

## Phase 3 — Quality Gate 🟢 AUTO

For each action item, validate:

| Check | Criterion |
| --- | --- |
| R1 | Text is specific enough to be actionable (not vague like "improve communication") |
| R2 | If R1 fails → flag item and suggest refinement |
| R3 | Owner resolved to team member email (or "Unassigned" if not found) |

Flag any items failing R1 and ask user to refine before proceeding.

---

## Phase 4 — Create Jira Tasks 🟢 AUTO

If `--dry-run` flag: display what would be created and stop.

**Summary format per task:** `[Retro Action] [category]: [text]`

**ADF structure** (use `templates-task.md` chore template):

```
🎯 Objective: [action text]
📋 Context: Retrospective action item from [sprint name]
🔗 Source: [page_url]
📅 Sprint: [current sprint name]

```

**Batch create** all tasks:

```python
jira_batch_create_issues(issues=[
    {
        "projectKey": "{{PROJECT_KEY}}",
        "issueType": "Task",
        "summary": "[Retro Action] [category]: [text]",
        "additional_fields": {
            "labels": ["retro-action"],
            "description": <ADF doc>
        }
    },
    ...
])
```

> **HR6:** `cache_invalidate(issue_key)` for each created task.

**Assign owners** (HR3: use acli):

```bash
# For each task with a resolved owner:
acli jira workitem assign -k "[KEY]" -a "[owner_email]" -y
```

**Add sprint** (HR7: always lookup sprint ID first):

```python
jira_get_sprints_from_board(board_id=<from config>, state="active")
# Then for each task:
jira_update_issue(issue_key="[KEY]", additional_fields={"{{SPRINT_FIELD}}": <sprint_id>})
```

> **HR6:** `cache_invalidate(issue_key)` after sprint assignment.

---

## Phase 5 — Link Tasks to Confluence Page 🟢 AUTO

Add a comment to the Confluence retrospective page listing all created tasks:

```
confluence_add_comment(page_id=<id>, body="""
## Action Items Created in Jira

| Task | Owner | Status |
|------|-------|--------|
| [KEY] — [summary] | [owner] | To Do |
...

Created: [today's date]
""")
```

---

## Phase 6 — Summary

```
## ✅ Retro Action Items Created ([N] tasks)

| Key | Summary | Owner |
|-----|---------|-------|
| [KEY] | [summary] | [owner] |
...

**Confluence page updated:** [page_url]

→ Tasks added to current sprint
→ Use /standup-digest tomorrow to track progress
```

---

## Flags

| Flag | Behavior |
| --- | --- |
| `--dry-run` | Parse and display action items without creating tasks |
| `--sprint <id>` | Override sprint assignment (HR7: still validates via lookup) |

---

## Common Scenarios

| Scenario | Command |
| --- | --- |
| From last sprint retro | `/retrospective-action-items 12345` |
| Preview only | `/retrospective-action-items 12345 --dry-run` |
| Interactive (search for page) | `/retrospective-action-items` |

---

## References

- [Task Template](../shared-references/templates-task.md) — chore template
- [Tools Reference](../shared-references/tools.md) — acli vs MCP
- [Sprint Frameworks](../shared-references/sprint-frameworks.md)
- After: `/standup-digest` next day to track action item progress
