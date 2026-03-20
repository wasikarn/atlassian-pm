---
name: bulk-reschedule
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache-server, mcp-atlassian, acli]
description: |
  Bulk-shift issue dates across a sprint or issue list — shifts start/due dates by N days or to a new start date.
  Uses existing sprint_set_fields.py script. Always previews before executing.
  Triggers: "reschedule", "shift dates", "bulk date", "move dates", "เลื่อนวัน"
argument-hint: "[--sprint <id>] [--issues <keys>] [--shift <+N|-N>] [--new-start <YYYY-MM-DD>]"
---

# /bulk-reschedule

**Role:** Scrum Master — Date Management
**Output:** Batch-updated issue dates with HR8 alignment verified

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`

> **Workflow Patterns:** See [workflow-patterns.md](../../shared-references/workflow-patterns.md)

## Phase 1 — Resolve Scope

Accept args: `--sprint <id>`, `--issues <BEP-123,BEP-124>`, `--shift <+7>` or `--new-start <date>`.

Must provide either `--sprint` or `--issues`. Must provide either `--shift` or `--new-start`.

If `--sprint`: fetch all issues + subtasks via `cache_sprint_issues` (fallback: `jira_get_sprint_issues`).
If `--issues`: `cache_get_issue` per key. Also fetch subtasks via JQL: `parent in (KEY1,KEY2)`.

For each issue: record `{{START_DATE_FIELD}}` (start) and `duedate`.

## Phase 2 — Compute New Dates

If `--shift +N`:

- `new_start = current_start + N days`
- `new_due = current_due + N days`

If `--new-start <date>`:

- Compute shift: `delta = new_start - current_start` (for first issue in range)
- Apply same delta to all issues

**⛔ GATE** — Display preview table before any changes:

```
| Key | Summary | Current Start | Current Due | New Start | New Due |
| BEP-123 | [summary] | 2026-03-20 | 2026-03-25 | 2026-03-27 | 2026-04-01 |
...
Total: X issues will be updated.
```

Confirm before proceeding.

## Phase 3 — HR8 Validate

For each subtask: check new dates are within parent story range.
Flag violations: "BEP-456 new due (2026-04-05) exceeds parent BEP-123 new due (2026-04-01)"

If violations found: offer options:

1. Adjust parent dates too (extend parent to cover subtask)
2. Cap subtask at parent boundary
3. Skip violating subtask

## Phase 4 — Execute

For each issue (batch by sprint if possible):

```bash
python3 scripts/sprint/sprint_set_fields.py \
  --issues BEP-123,BEP-124,BEP-125 \
  --start-date YYYY-MM-DD \
  --due-date YYYY-MM-DD
```

After each batch: HR6 `cache_invalidate(key)` for every updated issue.

## Phase 5 — Summary

🟡 REVIEW: Display:

- Updated: X issues
- Skipped (HR8 violation): Y issues [list]
- Any remaining misalignment warnings
