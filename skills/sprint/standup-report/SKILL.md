---
name: standup-report
disable-model-invocation: true
context: fork
agent: Explore
x-compatibility: [atlassian-cache, mcp-atlassian]
description: |
  Generate daily standup digest from active sprint — categorizes issues by status per assignee, flags anomalies.
  Optional --post flag posts digest as comment to sprint Confluence page.
  Triggers: "standup", "daily digest", "sprint status", "daily summary", "สรุป standup", "daily standup"
  Use when: generating a daily standup digest per assignee from the active sprint
  Do NOT use for: sprint planning (use plan-sprint); full retrospective (use the retrospective-analyst agent)
argument-hint: "[--sprint <id>] [--post]"
effort: low
---

# /standup-report

**Role:** Scrum Master — Daily Status
**Output:** Per-person standup digest with anomaly flags

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md)

## Phase 1 — Fetch Sprint Issues

1. If `--sprint` provided → use that ID. Else → `jira_get_sprints_from_board(board_id, state="active")` (HR7).
2. Try `cache_sprint_issues(sprint_id)` first. Fallback: `jira_get_sprint_issues(sprint_id)`.
3. Fields: `summary,status,assignee,issuetype,customfield_10016,{{START_DATE_FIELD}},duedate,updated,parent`
4. Calculate sprint day number: `(today - sprint_start_date).days + 1`

## Phase 2 — Categorize Per Person

For each team member with assigned issues:

- **Done (since yesterday):** status = "Done" AND `updated >= yesterday`
- **In Progress:** status = "In Progress"
- **Blocked:** status = "Blocked" OR has "Blocked" label
- **No Update:** status not "Done" AND `updated < yesterday` (stale)

## Phase 3 — Anomaly Detection

Flag these patterns:

- **Late Start:** issue status still "To Do" AND sprint_day > 6
- **Overdue:** `duedate < today` AND status ≠ "Done"
- **Stale:** no status change for > 2 days AND status = "In Progress"
- **Unassigned:** issue in sprint with no assignee

## Phase 4 — Output

🟡 REVIEW: Display digest per person (no emoji — plain text):

```
=== Standup Digest — [date] (Sprint Day [N]) ===

{{SLOT_2}}
  Done: {{PROJECT_KEY}}-123 [BE] User auth endpoint (3 SP)
  In Progress: {{PROJECT_KEY}}-124 [BE] JWT refresh flow (5 SP)
  Blocked: {{PROJECT_KEY}}-125 — blocked since Day 4

{{SLOT_3}}
  In Progress: {{PROJECT_KEY}}-130 [FE-Admin] Dashboard component (3 SP)
  No Update: {{PROJECT_KEY}}-131 [FE-Admin] Table pagination — no update 3 days ⚠

=== Anomalies ===

- {{PROJECT_KEY}}-132: Overdue (due 2026-03-18, still In Progress) — assignee: {{SLOT_4}}
- {{PROJECT_KEY}}-133: Late start (Day 7, still To Do) — unassigned
```

**If `--post` flag:** post this output as a comment on the sprint's Confluence page via `confluence_add_comment`.

## Examples

### Good

```text
/standup-report                       # resolves active sprint automatically via jira_get_sprints_from_board
/standup-report --sprint 46           # sprint ID obtained from jira_get_sprints_from_board(board_id={{BOARD_ID}}, state="active")
/standup-report --post                # generate digest and post it as a Confluence comment (review before using --post)
/standup-report --sprint 46 --post    # specific sprint + auto-post
```

### Bad

```text
/standup-report --sprint 46           # ❌ sprint ID hardcoded without calling jira_get_sprints_from_board first (HR7)
/standup-report                       # ❌ run when no active sprint exists — Phase 1 returns no issues
/standup-report --post                # ❌ using --post without reading the digest output first — always review before posting
/plan-sprint                          # ❌ wrong skill — /standup-report is a status snapshot; use /plan-sprint for workload decisions
```

**Common mistakes:**

- Running with `--post` without first reviewing the digest — anomaly flags may contain stale or incorrect data that should not be posted publicly
- Using the standup digest to make sprint planning decisions — this is a daily status snapshot, not a planning tool; use `/plan-sprint` for assignments
- Running multiple times a day expecting different results — Jira issue statuses are updated by the team, not by this skill
- Hardcoding a sprint ID instead of calling `jira_get_sprints_from_board(board_id={{BOARD_ID}}, state="active")` first (HR7)

## 🎓 Domain Expert Notes

### Why This Approach

The Scrum Guide 2020 redefined the Daily Scrum away from the classic three-question format: Developers now have full autonomy over structure, as long as the focus remains on the Sprint Goal and adaptation of the Sprint Backlog. This skill's anomaly detection (Phase 3) operationalizes that intent — surfacing deviations from the sprint plan that would otherwise go unnoticed until it's too late to adapt.

### Industry Frameworks Used

| Framework | Applied In | Why |
|-----------|-----------|-----|
| Scrum Guide 2020 Daily Scrum | Phase 2 categorization + Phase 3 anomalies | "Inspect progress toward the Sprint Goal and adapt the Sprint Backlog as necessary" — the digest maps issue statuses to this inspection purpose |
| Walk-the-Board format | Phase 4 output structure (per-person grouping) | More effective than three-question per-person format for teams >5; surfaces item-level status rather than activity narrative; preferred by modern Scrum practitioners |
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

## References

- [JQL Quick Reference](../../../references/jql-quick-ref.md) - JQL patterns for fetching in-progress and blocked issues
- [Sprint Frameworks](../../../references/sprint-frameworks.md) - Anomaly detection thresholds, velocity context
