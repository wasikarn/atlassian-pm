---
name: flow-check
context: fork
agent: general-purpose
model: haiku
x-compatibility: [mcp-atlassian, atlassian-cache]
allowed-tools:
  - mcp__mcp-atlassian__jira_search
  - mcp__mcp-atlassian__jira_transition_issue
  - mcp__plugin_atlassian-pm_atlassian-cache__cache_search
  - mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Board health snapshot and backlog replenishment for Scrumban workflow.

  Triggers: "flow check", "board health", "wip status", "replenish backlog", "ready queue", "ตรวจ board", "เติม backlog"
  Use when: checking WIP per column, triggering backlog replenishment when Ready queue is low, or identifying bottleneck columns (≥80% WIP capacity)
  Do NOT use for: sprint planning (use plan-sprint); closing a sprint (use close-sprint); standup digest (use standup-report)
argument-hint: "[--replenish]"
effort: low
memory: project
---

# /flow-check

**Role:** Flow Manager
**Output:** Board health table + replenishment action (if triggered)

## Dynamic Context

> Resolved at invocation time from `.claude/project-config.json`.

- **Project Key:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['project_key'])"`
- **Board Columns:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); cols=d.get('board',{}).get('columns',{}); [print(f'{k}: wip_max={v[\"wip_max\"]} statuses={v[\"statuses\"]}') for k,v in cols.items()]"`
- **Replenishment Threshold:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d.get('workflow',{}).get('replenishment_threshold', 4))"`

## Invocation Modes

- `/flow-check` — full snapshot: Phase 1 + Phase 2 + Phase 3
- `/flow-check --replenish` — Phase 2 only (fast path, auto-triggered on Done transitions)

---

## Phase 1 — Board Snapshot

**Goal:** Show current WIP per column vs limits so the team can see flow state at a glance.
**Required inputs:** Board columns config (Dynamic Context above)
**Constraints:** Read-only — no transitions in this phase
**Output:** WIP table with OK / WARN / FULL status per column

For each column in board config run:

```
jira_search(
  jql="project = \"<PROJECT_KEY>\" AND status IN (<statuses_quoted>)",
  fields="summary,assignee,status,key",
  max_results=50
)
```

Display:

```
Board Health — <today>

Column       | WIP | Max | Status
-------------|-----|-----|-------
Ready        |   5 |   6 | OK
In Progress  |   6 |   6 | FULL
Review       |   2 |   3 | OK
QA           |   1 |   3 | OK
```

Status: `OK` = count < wip_max · `WARN` = count ≥ 80% of wip_max · `FULL` = count ≥ wip_max

Skip Phase 1 if `--replenish` flag passed.

---

## Phase 2 — Replenishment Check

**Goal:** Determine if the Ready queue needs items pulled from Backlog.
**Required inputs:** Replenishment threshold from config (default 4)
**Constraints:** Transition items only after explicit user confirmation; HR6 — cache_invalidate after each transition; WIP gate fires on each Ready transition — set CLAUDE_WIP_CONFIRMED=\<key\>:Ready after confirming count < wip_max
**Output:** "Queue healthy" or top-5 WSJF-ranked candidates + confirmation prompt

Count current Ready items (from Phase 1 or re-query if `--replenish` fast path).

**If Ready count ≥ threshold:**

```
Queue healthy (X/<threshold> items). No action needed.
```

**If Ready count < threshold**, fetch top candidates:

```
jira_search(
  jql="project = \"<PROJECT_KEY>\" AND status = \"Backlog\"
       AND issuetype in (Story, Task)
       ORDER BY priority DESC, story_points ASC",
  fields="summary,priority,customfield_10016,key",
  max_results=10
)
```

Compute WSJF score ≈ priority_weight / story_points (Highest=5, High=4, Medium=3, Low=2). Display top 5:

```
Ready queue low (X/<threshold> items). Top backlog candidates:

1. {{PROJECT_KEY}}-55 — Add payment retry [High, 3 SP, WSJF≈1.33]
2. {{PROJECT_KEY}}-61 — Fix login timeout [Highest, 5 SP, WSJF≈1.00]
...

Move to Ready? Enter numbers (e.g. "1,3") or "none" to skip:
```

For each confirmed item: `jira_transition_issue(issue_key, transition="Ready")` then `cache_invalidate(issue_key)` (HR6).

---

## Phase 3 — Bottleneck Alert

**Goal:** Surface aging items in columns approaching capacity before they become hard blocks.
**Required inputs:** Phase 1 WIP counts
**Constraints:** Read-only — no transitions
**Output:** Aging items in bottleneck columns with assignee + days-open

Skip Phase 3 if `--replenish` flag passed.

For each column where `count ≥ wip_max × 0.8`:

```
jira_search(
  jql="project = \"<PROJECT_KEY>\" AND status IN (<statuses_quoted>) ORDER BY created ASC",
  fields="summary,assignee,created,key",
  max_results=20
)
```

Display oldest items with assignee and age (days since created):

```
⚠️  Bottleneck: In Progress (6/6 FULL)
Oldest items:
  {{PROJECT_KEY}}-38 — Migrate auth service (joakim) — 8 days
  {{PROJECT_KEY}}-42 — Admin dashboard refactor (wanchalerm) — 6 days
→ Suggest: Swarm on {{PROJECT_KEY}}-38 to unblock flow.
```

## Memory Usage

When memory is active, track:

- WIP violations that occurred in previous flow checks (trend: "column X has been over WIP for 3 days")
- Bottlenecks that persist across checks (flag as systemic, not temporary)
