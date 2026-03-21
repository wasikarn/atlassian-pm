---
name: standup-report
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache, mcp-atlassian]
description: |
  Generate daily standup digest from active sprint — categorizes issues by status per assignee, flags anomalies.
  Optional --post flag posts digest as comment to sprint Confluence page.
  Triggers: "standup", "daily digest", "sprint status", "daily summary", "สรุป standup"
argument-hint: "[--sprint <id>] [--post]"
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
/standup-report --sprint 46           # sprint ID obtained from jira_get_sprints_from_board(board_id=2, state="active")
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
- Hardcoding a sprint ID instead of calling `jira_get_sprints_from_board(board_id=2, state="active")` first (HR7)
