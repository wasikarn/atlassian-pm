---
name: apm-reschedule-sprint
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
description: |
  Bulk-shift issue dates across a sprint or issue list — shifts start/due dates by N days or to a new start date.
  Uses existing sprint_set_fields.py script. Always previews before executing.
  Triggers: "reschedule", "shift dates", "bulk date", "move dates", "เลื่อนวัน", "push sprint dates"
  Use when: bulk-shifting issue dates across a sprint or issue list by N days or to a new start date
  Do NOT use for: sprint capacity planning (use plan-sprint); closing a sprint (use close-sprint)
argument-hint: "[--sprint <id>] [--issues <keys>] [--shift <+N|-N>] [--new-start <YYYY-MM-DD>]"
effort: medium
---

# /atlassian-pm:apm-reschedule-sprint

**Role:** Scrum Master — Date Management
**Output:** Batch-updated issue dates with HR8 alignment verified

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Project Key:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['project_key'])"`

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md)

## Phase 1 — Resolve Scope

Accept args: `--sprint <id>`, `--issues <{{PROJECT_KEY}}-123,{{PROJECT_KEY}}-124>`, `--shift <+7>` or `--new-start <date>`.

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
| {{PROJECT_KEY}}-123 | [summary] | 2026-03-20 | 2026-03-25 | 2026-03-27 | 2026-04-01 |
...
Total: X issues will be updated.
```

Confirm before proceeding.

## Phase 3 — HR8 Validate

For each subtask: check new dates are within parent story range.
Flag violations: "{{PROJECT_KEY}}-456 new due (2026-04-05) exceeds parent {{PROJECT_KEY}}-123 new due (2026-04-01)"

If violations found: offer options:

1. Adjust parent dates too (extend parent to cover subtask)
2. Cap subtask at parent boundary
3. Skip violating subtask

## Phase 4 — Execute

For each issue (batch by sprint if possible):

```bash
python3 scripts/sprint/sprint_set_fields.py \
  --issues {{PROJECT_KEY}}-123,{{PROJECT_KEY}}-124,{{PROJECT_KEY}}-125 \
  --start-date YYYY-MM-DD \
  --due-date YYYY-MM-DD
```

After each batch: HR6 `cache_invalidate(key)` for every updated issue.

## Phase 5 — Summary

🟡 REVIEW: Display:

- Updated: X issues
- Skipped (HR8 violation): Y issues [list]
- Any remaining misalignment warnings

## Examples

### Good

```text
/reschedule-sprint --sprint 47 --shift +7               # shift all sprint issues forward 7 days; sprint ID from jira_get_sprints_from_board
/reschedule-sprint --sprint 47 --new-start 2026-04-07   # shift to a new start date; delta applied uniformly to all issues
/reschedule-sprint --issues {{PROJECT_KEY}}-210,{{PROJECT_KEY}}-211 --shift +3  # shift specific stories (and their subtasks) by 3 days
/reschedule-sprint --issues {{PROJECT_KEY}}-210 --new-start 2026-04-01  # reschedule a single story to a new start date
```

### Bad

```text
/reschedule-sprint --sprint 47 --shift +7               # ❌ sprint ID hardcoded without calling jira_get_sprints_from_board first (HR7)
/reschedule-sprint --sprint 47 --shift +7 --new-start 2026-04-07  # ❌ conflicting flags — use --shift OR --new-start, not both
/reschedule-sprint --issues {{PROJECT_KEY}}-456 --shift +5          # ❌ rescheduling subtask without shifting parent first — new due date may violate HR8
/reschedule-sprint --sprint 47 --shift +14              # ❌ confirmed without reviewing the preview table — always inspect before confirming
```

**Common mistakes:**

- Using `--shift` and `--new-start` together — they are mutually exclusive; providing both causes ambiguous delta calculation
- Rescheduling subtasks (`{{PROJECT_KEY}}-456`) independently when their parent story (`{{PROJECT_KEY}}-210`) also needs to move — reschedule the parent first, then subtasks will be validated against the updated parent range (HR8)
- Approving the Phase 2 preview without checking for HR8 violations — the preview gate exists precisely to catch subtask-exceeds-parent issues before writes happen
- Not calling `cache_invalidate(key)` after each batch update — stale cache causes incorrect date reads in verify and planning tools (HR6)

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)

## References

- [HR Rules](../../../references/hr-rules.md) - HR6 cache invalidation (required after every date update)
- [JQL Quick Reference](../../../references/jql-quick-ref.md) - JQL patterns for fetching sprint issues by date range
