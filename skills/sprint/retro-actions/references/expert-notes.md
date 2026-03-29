## 🎓 Domain Expert Notes

### Why This Approach

The biggest failure mode in retrospectives is action items that never become work. Research by Esther Derby and Diana Larsen (*Agile Retrospectives*, 2006) shows that the primary reason retro actions fail is lack of ownership and no integration into the team's backlog. Converting action items to first-class Jira tasks with priority and sprint assignment closes this loop mechanically.

### Industry Frameworks Used

| Framework | Applied In | Why |
|-----------|-----------|-----|
| SMART Criteria (Doran, 1981) | Phase 1 validation — title/description length + specificity check | Action items must be Specific, Measurable, Assignable, Realistic, Time-bound to be actionable |
| Agile Retrospectives (Derby/Larsen) | Phase 3 — `[Retro]` prefix + sprint label | Traceable retro actions are a core Derby/Larsen pattern; labeling by sprint enables trend analysis across retrospectives |
| DORA Metrics | Phase 3 — `retro-action` label | Aggregating retro action completion rate over sprints is a proxy for team improvement velocity |

### Key Metrics

- **Action Item Completion Rate:** retro tasks closed by next sprint end / total retro tasks created — target: ≥ 80%; below 60% indicates planning overcommitment or lack of ownership
- **Recurrence Rate:** same action item type appearing in 2+ consecutive sprints — flag as systemic issue requiring process change, not just a task
- **Time-to-assign:** retro task assigned within 24h of creation — unassigned tasks have ~3× higher abandonment rate

### Expert Decision Criteria

- **If all 5 action items are "high" priority:** challenge the team — forced ranking prevents priority inflation. At most 2 items should be high.
- **If `assignee_hint` is "team" for every item:** no accountability. Push back: who specifically owns this? "Team" ownership = no ownership.
- **If a retro action from the previous sprint recurs:** do not create a new task — update the existing one with a comment. Duplicate tasks dilute the backlog.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Retro tasks never completed | No owner assigned; buried in backlog | Assign immediately after creation; add to next sprint at planning |
| Same action item every sprint | Root cause not addressed — symptom-level fix only | Escalate to process change or team agreement, not another task |
| ADF description rejected | Missing required fields or malformed JSON | Validate ADF structure in Phase 3 before calling `jira_create_issue` |
| Duplicate tasks across sprints | `--dry-run` skipped; dedup JQL too narrow | Always run `--dry-run` first; widen JQL to 60d lookback if needed |
