---
name: close-sprint
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Close an active sprint systematically — triage incomplete issues, execute moves, close sprint, generate Confluence review page.
  Distinct from retrospective-analyst (analysis only). This skill EXECUTES the closure.
  Triggers: "close sprint", "end sprint", "sprint closure", "ปิด sprint"
  Use when: a sprint is ending and needs to be officially closed — issues moved, sprint status updated, Confluence review page created.
  Do NOT use for: retrospective analysis only (use retrospective-analyst); planning the next sprint (use plan-sprint).
argument-hint: "[--sprint <id>]"
effort: high
---

# /close-sprint

**Role:** Scrum Master — Sprint Closure Execution
**Output:** Closed sprint + Confluence sprint review page + velocity update

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`
- **Board ID:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['board_id'])"`

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
3. `jira_get_sprint_issues(sprint_id)` — fields: `summary,status,assignee,issuetype,customfield_10016,{{START_DATE_FIELD}},duedate,parent,labels`
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

Get next sprint: `jira_get_sprints_from_board(state="future")`

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

> **🟢 PARALLEL** — Phase 6 (Confluence page) and Phase 7 (velocity-tracker) have no dependency on each other — both consume data from Phase 2/4. Launch them simultaneously after Phase 5 sprint close.

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

If velocity-tracker not available → skip and note in Phase 8 summary.

## Phase 8 — Summary

> **🟢 AUTO** — Record sprint health metrics to persistent history before displaying summary:
>
> ```bash
> python scripts/sprint_health_record.py \
>   --sprint-id SPRINT_ID \
>   --sprint-name "SPRINT_NAME" \
>   --planned-sp PLANNED_SP \
>   --completed-sp COMPLETED_SP \
>   --carry-over-count CARRY_OVER_COUNT \
>   --carry-over-sp CARRY_OVER_SP \
>   --total-issues TOTAL_ISSUES \
>   --done-issues DONE_ISSUES
> ```
>
> Then record per-story outcomes:
>
> ```bash
> python scripts/story_outcome_record.py \
>   --sprint-id SPRINT_ID \
>   --sprint-name "SPRINT_NAME" \
>   --issues-json 'JSON_ARRAY'
> ```
>
> Build `JSON_ARRAY` from Phase 1 `issue_list`: `key`, `summary`, `status`, `sp` (customfield\_10016), `assignee` (displayName), `issuetype` (name), `labels`. Include all sprint issues (done and incomplete).
>
> Then spawn calibration update in the background (non-blocking):
>
> ```bash
> nohup uv run scripts/ai/calibrate.py > /dev/null 2>> "${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/atlassian-pm-atlassian-pm}/calibrate.log" &
> ```
>
> Print `[calibration scheduled in background]` and continue immediately — do NOT wait for it to finish.
>
> If calibrate skips (< 10 new records or < 7 days since last run), it exits on its own — not a blocker.

🟡 REVIEW: Display:

- Sprint [name] closed
- Velocity: X/Y SP (Z% completion)
- Carry-over: N issues moved to next sprint, M to backlog
- Review page: [Confluence link]
- Next: run `/atlassian-pm:retrospective-analyst [sprint-id]` for deeper analysis

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)


## References

[Sprint Frameworks](../../../references/sprint-frameworks.md) · [Team Capacity](../../../references/team-capacity.md) · [Skill Orchestration](../../../references/skill-orchestration.md) · [Mermaid Guide](../../../references/mermaid-guide.md)
