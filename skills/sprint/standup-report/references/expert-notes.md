## 🎓 Domain Expert Notes

### Why This Approach

The Scrum Guide 2020 redefined the Daily Scrum away from the classic three-question format: Developers now have full autonomy over structure, as long as the focus remains on the Sprint Goal and adaptation of the Sprint Backlog. This skill's anomaly detection (Phase 3) operationalizes that intent — surfacing deviations from the sprint plan that would otherwise go unnoticed until it's too late to adapt.

### Industry Frameworks Used

| Framework | Applied In | Why |
|-----------|-----------|-----|
| Scrum Guide 2020 Daily Scrum | Phase 2 categorization + Phase 3 anomalies | "Inspect progress toward the Sprint Goal and adapt the Sprint Backlog as necessary" — the digest maps issue statuses to this inspection purpose |
| Walk-the-Board format (Scrum.org community, attributed to Jeff Sutherland's teams; documented in "Scrum: The Art of Doing Twice the Work in Half the Time", 2014) | Phase 4 output structure (per-person grouping) | Walk-the-board = discuss each Kanban column right-to-left (Done → In Progress → To Do) rather than person-by-person; surfaces blockers and flow issues earlier. More effective than three-question format for teams >5; scrum.org explicitly recommends it as an alternative structure |
| Impediment Management (separate channel) | Phase 3 anomaly detection → Phase 4 flagging | Scrum Guide pattern: surface blockers in the daily, but solve them in a follow-up meeting with only relevant parties; the digest flags blockers without embedding the solution discussion |
| DORA — Change Lead Time | Phase 3 Stale detection (>2 days no update) | Stale items are leading indicators of degraded change lead time; an In-Progress item with no update for 2+ days is typically stuck in review, merge conflict, or environment issue |
| Psychological Safety (Edmondson) | Phase 4 output design (plain text, no blame framing) | Research published in 2025 confirms daily stand-ups have a statistically significant positive effect on psychological safety when they create a safe sharing environment; anomaly flags are framed as observations, not accusations |

### Key Metrics

- **Sprint Day Number:** (today − sprint start) + 1 — provides burndown context; an issue still "To Do" on Day 7 of a 10-day sprint is a different risk level than on Day 2
- **Stale Rate:** (issues with no update > 2 days) / total In-Progress × 100 — healthy: 0%; >20% indicates the team is not updating Jira or is stuck without surfacing impediments
- **Blocked Issue Count:** absolute count of Blocked status + "Blocked" label — any non-zero count is an action item for the Scrum Master; blockers older than 1 day with no owner = systemic problem
- **Late Start Rate:** issues still "To Do" on sprint Day 6+ / total sprint items × 100 — >15% signals sprint was over-committed or items were not ready at planning
- **Overdue Count:** issues where duedate < today and status != Done — leading indicator of sprint goal risk; should trigger immediate replanning discussion if >2

### Expert Decision Criteria

- **If blocked issue age > 2 days:** the Scrum Master must take direct action, not just flag in the digest — unblocking is the Scrum Master's primary sprint-execution responsibility
- **If stale > 2 days AND status = In Progress:** the issue is likely in a hidden blocked state; the developer may not know how to surface it — create psychological safety to ask directly in the standup
- **If >3 overdue issues appear:** do not just post the digest — trigger a sprint health conversation with the Product Owner before the next standup
- **If all issues for one person are "No Update":** the person may be off, overloaded, or the issues are mis-assigned — verify assignee attendance before posting public anomaly flags
- **If using --post flag:** always read the digest output first; anomaly flags contain issue keys, dates, and assignee names — review for accuracy before making them visible to the wider team

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Standup becomes a status read-out, not a coordination event | Digest replaces conversation instead of preparing for it | Use the digest as pre-read 15 minutes before standup, not as a substitute; the meeting is for adaptation decisions, not recitation |
| Anomaly flags are ignored sprint after sprint | No owner assigned to act on flags | Each anomaly flag must map to a named action owner (usually Scrum Master for blockers, Scrum Master + PO for overdue) |
| "No Update" flags on items that were actually worked | Developers not updating Jira status | The digest measures Jira data quality as a side effect; "No Update" anomalies drive Jira hygiene improvement over time |
| --post sends draft/incorrect digest | Digest not reviewed before posting | Always generate without --post first; treat --post as a one-way publish action requiring explicit review gate |
| Daily Scrum exceeds 15 minutes | Digest not used as prep; problem-solving happens in the meeting | Surface the digest before the meeting; move any impediment resolution to a post-standup follow-up with only relevant parties |

### Authoritative References

- **Scrum Guide 2020 (Sutherland/Schwaber):** "The Daily Scrum is a 15-minute event for the Developers of the Scrum Team. [...] The structure of the event is set by the Developers and can be conducted in different ways if their focus is on progress toward the Sprint Goal."
- **Scrum.org — Going Beyond Three Questions:** "The three-question format is no longer in the Scrum Guide. Teams are encouraged to select structures that best inspect their progress toward the Sprint Goal — walking the board is often more effective."
- **Edmondson (2025, European Journal of Work and Organizational Psychology):** Daily stand-ups have a statistically significant positive effect on psychological safety perceptions — the framing of updates as observations, not evaluations, is critical to maintaining this benefit

---
