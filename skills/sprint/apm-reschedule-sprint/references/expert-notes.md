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
