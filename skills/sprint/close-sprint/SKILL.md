---
name: close-sprint
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Close an active sprint systematically — triage incomplete issues, execute moves, close sprint, generate Confluence review page.
  Distinct from retrospective-analyst (analysis only). This skill EXECUTES the closure.
  Triggers: "close sprint", "end sprint", "sprint closure", "ปิด sprint"
argument-hint: "[--sprint <id>]"
effort: high
---

# /close-sprint

**Role:** Scrum Master — Sprint Closure Execution
**Output:** Closed sprint + Confluence sprint review page + velocity update

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Fetch | `sprint_id`, `sprint_name`, `sprint_data`, `issue_list[]` |
| 2. Triage | `done_issues[]`, `incomplete_issues[]`, `blocked_issues[]` |
| 3. Move Plan | `move_plan[]` (per-issue: destination + next_sprint_id) |
| 4. Execute | `move_results` (moved/failed/skipped) |
| 5. Close | `sprint_closed: bool` |
| 6. Review Page | `confluence_page_url` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md)

## Phase 1 — Fetch Sprint Data

1. If `--sprint` flag provided → use that sprint ID.
2. Else → `jira_get_sprints_from_board(board_id, state="active")` (HR7: never hardcode sprint ID)
3. `jira_get_sprint_issues(sprint_id)` — fetch all issues with fields: `summary,status,assignee,issuetype,customfield_10016,{{START_DATE_FIELD}},duedate,parent`
4. Display sprint summary: name, dates, total issues, SP breakdown

## Phase 2 — Triage

Categorize:

- **Done:** status = "Done" / "Closed"
- **Incomplete:** status ≠ "Done" (In Progress, To Do, etc.)
- **Blocked:** has "Blocked" label or status = "Blocked"

Display triage table:

```
| Status | Count | SP |
| Done | X | Y |
| Incomplete | X | Y |
| Blocked | X | Y |
```

Carry-over rate: `incomplete_count / total_count * 100%`

## Phase 3 — Move Plan

🟡 REVIEW gate: for each incomplete issue, propose destination:

- Blocked issues → backlog (default)
- In Progress → next sprint (default)
- To Do → backlog (default)

Display proposal table:

```
| Key | Summary | SP | Current Status | Proposed Move |
```

**⛔ GATE** — Wait for user to confirm or adjust move destinations before proceeding.

## Phase 4 — Execute Moves

`Agent(name: "sprint-transition-agent"): sprint_id, move_plan`

Display result: "Moved: X to next sprint | Y to backlog | Z failed"

If any failed → show failed keys + error, ask user to resolve manually before continuing.

## Phase 5 — Close Sprint

Show: "Ready to close sprint [name]. This is irreversible."

**⛔ GATE** — Explicit user confirm required.

1. `jira_update_sprint(sprint_id, state="closed")` (MCP: `mcp__mcp-atlassian__jira_update_sprint`)
2. HR6: `cache_invalidate(sprint_id)` (note: jira_update_sprint is in HR6 matcher)

## Phase 6 — Confluence Review Page

Create Confluence page in {{PROJECT_KEY}} space: "Sprint [name] Review"

Page structure:

- **Header:** Sprint name, dates, goal
- **Velocity:** Planned SP / Completed SP / Carry-over %
- **Completed Issues:** table of Done items with assignee + SP
- **Carry-over:** table of moved items + where they went
- **Anomalies:** blocked issues, late starts, stale items

Use `confluence_create_page` (HR4: no macros via MCP — plain storage format).

## Phase 7 — Metrics Update

`Agent(name: "velocity-tracker"): sprint_id, planned_sp, completed_sp, carry_over_count, sprint_end_date`

Records velocity data for trend analysis. If velocity-tracker is not available (agent not found), skip this phase and note in summary.

## Phase 8 — Summary

🟡 REVIEW: Display:

- Sprint [name] closed
- Velocity: X/Y SP (Z% completion)
- Carry-over: N issues moved to next sprint, M to backlog
- Review page: [Confluence link]
- Next: run `/atlassian-pm:retrospective-analyst [sprint-id]` for deeper analysis

## Examples

### Good

```text
/close-sprint                         # interactive — resolves active sprint via jira_get_sprints_from_board automatically
/close-sprint --sprint 45             # sprint ID obtained from jira_get_sprints_from_board(board_id=2, state="active")
```

### Bad

```text
/close-sprint --sprint 45             # ❌ sprint ID hardcoded without calling jira_get_sprints_from_board first (HR7)
/close-sprint                         # ❌ run when no active sprint exists — Phase 1 will fail with no results
/close-sprint                         # ❌ run before resolving all P1 bugs — closing locks the sprint irreversibly
/retrospective-analyst                # ❌ wrong skill — /retrospective-analyst is analysis only; /close-sprint EXECUTES closure
```

**Common mistakes:**

- Skipping the Phase 3 GATE — the move plan must be reviewed and confirmed before executing; auto-approving leads to issues moved to wrong destinations
- Closing the sprint before all P1/critical bugs are resolved — the close operation (Phase 5) is irreversible
- Expecting `/close-sprint` to produce retrospective analysis — use `/atlassian-pm:retrospective-analyst` for that after closure
- Not calling `cache_invalidate(sprint_id)` after `jira_update_sprint` — stale cache causes wrong sprint state in subsequent reads (HR6)

## 🎓 Domain Expert Notes

### Why This Approach

Sprint closure is a hard boundary event in Scrum — the Scrum Guide (2020) defines the Sprint Retrospective as the final event that concludes the Sprint. Executing closure as a distinct, irreversible operation (rather than a soft archive) enforces accountability: carry-over rate and velocity are recorded at a fixed point in time, enabling honest trend analysis.

### Industry Frameworks Used

| Framework | Applied In | Why |
|-----------|-----------|-----|
| Scrum Guide 2020 Sprint Retrospective | Phase 2 Triage + Phase 7 Metrics | Inspects "what went well, what problems, how solved" — maps directly to Done/Incomplete/Blocked categories |
| Yesterday's Weather (Scrum pattern) | Phase 7 velocity-tracker | Team velocity is the running average of recent sprints (±20% precision); single-sprint data is noise |
| DORA Metrics (Google DevOps Research) | Phase 6 Review Page — Anomalies section | Deployment frequency and change lead time surface in blocked/late-start anomalies; carry-over rate is a proxy for delivery predictability |
| Start/Stop/Continue (retrospective) | Post-closure: feeds `/retrospective-analyst` | Simplest actionable retro format; each action maps to a backlog item or team agreement |
| 4Ls (Liked/Learned/Lacked/Longed For) | Optional retro input after page is generated | Richer emotional signal; useful when velocity is stable but morale is low |

### Key Metrics

- **Sprint Velocity:** SP completed / sprint — target: consistent ±15% of rolling 3-sprint average; spikes >30% indicate scope inflation or counting errors
- **Carry-over Rate:** incomplete / total issues × 100% — healthy: <15%; >30% signals systemic planning overcommitment or blocking dependencies
- **Completion Ratio:** done SP / planned SP — the primary predictability signal; teams with >80% completion consistently outperform on delivery dates
- **Blocked Issue Age:** days an issue has been in Blocked status — >2 days with no resolution attempt = Scrum Master action required
- **DORA Deployment Frequency:** how often code ships per sprint — correlates with carry-over rate; teams that ship daily have <10% carry-over

### Expert Decision Criteria

- **If carry-over rate > 30% for 2+ consecutive sprints:** trigger a planning review — root cause is almost always over-commitment, not execution failure
- **If a blocked issue is moving to the next sprint:** it MUST have a concrete unblocking owner before the move, not just a destination sprint
- **If completed SP < 50% of planned SP:** do not close without a stakeholder notification — this is a delivery risk event, not a routine closure
- **If velocity drops >25% from prior sprint:** flag as anomaly in the Confluence review page before the retrospective, not after
- **Carry-over to next sprint vs. backlog:** In-Progress items default to next sprint only if they have >50% work complete (estimated); otherwise backlog is more honest

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Carry-over rate consistently >30% | Sprint overcommitment; velocity-based capacity not applied | Apply Yesterday's Weather: cap commitment at 80% of 3-sprint avg velocity |
| Velocity appears high but carry-over is also high | SP claimed on partial work; Definition of Done not enforced | Only count SP on issues with status = Done at close time; partial credit is a metric corruption |
| Retrospective insights never actioned | Actions not converted to Jira items with owners | Every retro action item → Jira task in next sprint backlog, assigned at closure |
| Sprint closed with P1 bugs still open | Urgency pressure; no gate before close | HR: enforce pre-close check for open P1/P2 issues; closure is irreversible |
| Confluence review page never read | Page created but not linked or announced | Post link in team channel at closure; add it to the next sprint's Definition of Done checklist |

### Authoritative References

- **Scrum Guide 2020 (Sutherland/Schwaber):** "The Sprint Retrospective concludes the Sprint. It is timeboxed to a maximum of three hours for a one-month Sprint." — closure order matters: retro before close is the correct sequence
- **Accelerate (Forsgren, Humble, Kim):** The four DORA metrics — deployment frequency, lead time, change fail rate, recovery time — are the only engineering metrics proven to correlate with organizational performance; carry-over rate is a leading indicator of degraded deployment frequency
- **Scrum Patterns (Coplien/Harrison):** Yesterday's Weather — "use the team's recent velocity as the primary forecast signal; adjust only for known capacity changes (leave, team size)"
