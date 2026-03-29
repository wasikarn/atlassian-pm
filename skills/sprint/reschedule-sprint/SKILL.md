---
name: reschedule-sprint
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

# /reschedule-sprint

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

### Why This Approach

Sprint date rescheduling is a scope change management operation, not a planning operation. The Scrum Guide 2020 is explicit: "No changes are made that would endanger the Sprint Goal" — rescheduling dates preserves the Sprint Goal while adjusting the execution timeline. The preview gate (Phase 2) exists precisely because date shifts have cascading effects on subtask alignment (HR8), and a batch write without review is a data integrity risk.

### Industry Frameworks Used

| Framework | Applied In | Why |
|-----------|-----------|-----|
| Scrum Guide 2020 — Sprint Goal Protection | Phase 2 GATE design | Date shifts must not change the sprint goal; they change how/when work is done, not what value is delivered |
| Impact Assessment Framework | Phase 2 preview table | Forces explicit visualization of all downstream date changes before any write; borrowed from change management (ITIL) — "understand scope of change before executing" |
| HR8 Subtask Alignment (internal) | Phase 3 validation | Subtask dates must be within parent story range; violation creates burndown miscalculation and misleading due-date alerts in Jira |
| Uniform Delta Shift | Phase 2 computation | Apply the same delta to all issues in scope to preserve relative sequencing; non-uniform shifts require a full replanning cycle, not a reschedule |

### Key Metrics

- **Shift Magnitude:** the N-day delta — shifts >5 days typically signal a sprint replanning event (scope too large to absorb), not a date adjustment
- **HR8 Violation Rate:** count of subtasks whose new due date would exceed parent — healthy: 0; any violation requires an explicit decision (extend parent / cap subtask / skip)
- **Issues Updated vs. Skipped:** track skipped-due-to-violation ratio; >20% skipped means the scope selection was wrong (reschedule parent before subtasks)
- **Buffer Remaining:** sprint end date − latest new due date — must be >0 after reschedule; negative buffer means the sprint goal is now at risk

### Expert Decision Criteria

- **If shift > 5 working days:** question whether this is a reschedule or a sprint cancellation/replanning event. The Scrum Guide (2020) explicitly allows the Product Owner to cancel a sprint when "the Sprint Goal becomes obsolete" — a >1-week shift often signals the goal is no longer achievable in the current sprint, making cancellation + replanning the more honest choice over a date-shift patch
- **If rescheduling a subtask before its parent:** always reschedule the parent story first, then run the subtask validation — the reverse order produces guaranteed HR8 violations
- **If an issue has no start date ({{START_DATE_FIELD}} is null):** skip it in the delta calculation; null + delta = incorrect anchor; surface as a warning, not an error
- **If the new due date of any issue exceeds the sprint end date:** flag it before writing — an issue due after sprint end will never appear on the burndown correctly and will auto-carry-over
- **If stakeholders are expecting specific delivery dates:** communicate the shift explicitly before executing; a date change in Jira without stakeholder awareness is the most common source of delivery expectation mismatches

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Subtask due dates exceed parent after shift | Subtasks rescheduled without parent | Always scope `--issues` to include the parent story; subtasks are fetched automatically via JQL |
| Shift applied inconsistently across issues | Mix of `--shift` and manual date edits | Use only one mechanism per batch; mixed approaches produce inconsistent relative ordering |
| Stakeholders surprised by date changes | Reschedule executed without communication | Treat Phase 2 preview table as a stakeholder communication artifact, not just an internal check |
| Sprint burndown shows incorrect trajectory after reschedule | Cache not invalidated after batch write (HR6) | Always `cache_invalidate(key)` for every updated issue immediately after Phase 4; stale cache corrupts `/standup-report` and `/verify-issue` reads |
| Issues rescheduled past sprint end date | No boundary check performed | Phase 3 should include a sprint-end boundary check; any new due date > sprint end date = escalate to replanning |

### Authoritative References

- **Scrum Guide 2020:** "Only the Developers can change their Sprint Backlog during the Sprint. The Developers may find that they have more or less work than expected, and scope may be clarified and re-negotiated between the Product Owner and Development Team as more is learned." — date shifts are scope clarification, not scope change
- **ITIL 4 Change Enablement (Axelos, 2019):** The ITIL principle that every change requires impact assessment and a rollback path before execution is the inspiration for the Phase 2 preview gate (paraphrased from ITIL 4 change practice guidance, not a verbatim quote). The gate produces an impact table (what will change) and leaves the reschedule reversible (delta can be negated) — meeting ITIL's spirit for a standard change category
- **Mike Cohn (Agile Estimating and Planning):** "A plan is a snapshot of your best understanding at a point in time, not a contract" — rescheduling is routine; the discipline is in the visibility of the shift, not in avoiding it

---

## References

- [HR Rules](../../../references/hr-rules.md) - HR6 cache invalidation (required after every date update)
- [JQL Quick Reference](../../../references/jql-quick-ref.md) - JQL patterns for fetching sprint issues by date range
