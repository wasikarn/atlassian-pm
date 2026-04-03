---
name: plan-sprint
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
description: |
  This skill plans a new sprint — calculating team capacity, analyzing carry-over items, prioritizing backlog, distributing work, and committing assignments to Jira using a 9-phase workflow.

  Triggers: "plan sprint", "sprint planning", "start new sprint", "begin sprint", "capacity planning", "assign work", "workload distribution", "what should we work on this sprint", "วางแผน sprint", "จัดสรรงาน"
  Use when: planning a new sprint — fetching carry-over items, calculating team capacity, distributing work, and committing assignments to Jira
  Do NOT use for: generating a standup digest (use standup-report); closing or reviewing a completed sprint (use close-sprint)
argument-hint: "[--sprint <id>] [--carry-over-only]"
effort: high
---

# /plan-sprint

**Role:** Scrum Master + Sprint Planner
**Output:** Sprint plan with assignments executed in Jira

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Board ID:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['board_id'])"`

## Pre-Meeting Checklist

> See [references/pre-meeting-checklist.md](references/pre-meeting-checklist.md)

## ⚠️ Critical: Capacity Before Assignment

Order: Calculate capacity (Phase 2) → Prioritize backlog (Phase 4) → Assign (Phase 5). Assigning first causes burnout and missed commitments.

## Context Object

| Phase | Adds to Context |
| ----- | --------------- |
| 1. Discovery | `source_sprint`, `target_sprint`, `sprint_items[]` |
| 2. Capacity | `capacity_table[]`, `available_slots[]` |
| 3. Carry-over | `carry_over_items[]`, `probability_scores[]` |
| 4. Prioritize | `prioritized_items[]`, `vs_validated` |
| 5. Distribute | `assignment_map[]`, `workload_table` |
| 6. Risk | `risk_flags[]`, `mitigations[]` |
| 7. Risk Forecast | `risk_forecast_result`, `mitigations_applied[]` |
| 8. Review | `approved_plan` |
| 9. Execute | `execution_log[]`, `assigned_keys[]` |

> See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels, QG Scoring, and Annotation Cycle.

## Part A: Data Collection (Phases 1-2)

### 1. Sprint Discovery

Ask: which target sprint (default → next future) and source sprint for carry-over (default → active).
HR7: NEVER hardcode sprint IDs — always `jira_get_sprints_from_board(board_id, state="future")`.

> **🟢 PARALLEL** — fetch source and target sprint issues simultaneously:

```text
jira_get_sprint_issues(sprint_id="<source>", fields="summary,status,assignee,priority,issuetype,customfield_10016,timetracking,{{START_DATE_FIELD}},duedate")
jira_get_sprint_issues(sprint_id="<target>", fields="summary,status,assignee,priority,issuetype,customfield_10016,timetracking,{{START_DATE_FIELD}},duedate")
```

**🟡 REVIEW** — Present data summary. Proceed unless user objects.

### 2. Team Capacity

```text
Read: ../../../references/team-capacity.md
Read: .claude/project-config.json → team.members[], team.avg_throughput_per_sprint
Read: .claude/project-config-team-detail.json → review_cost, growth_tracks, bus_factor, velocity.throughput_history
```

**Optional:** If backlog has 10+ unplanned issues, offer to run backlog-groomer agent before planning. Issues flagged "Needs AC", "Missing Estimate", or "Blocked" must NOT be committed.

**Step 1 — Velocity:**

```text
Sprint Capacity = avg_velocity × 0.8   (or avg_throughput_per_sprint if no velocity history)
```

**Step 2 — Individual Hours:**

```text
Productive Hours = sprint_length_days × 8h × focus_factor - (leave_days × 8h × focus_factor)
Review Load = count(reviewees) × review_cost.hours_per_junior_per_sprint
Already Assigned = sum(timetracking.originalEstimate) of current sprint subtasks
Net Available = Productive Hours - Review Load - Already Assigned
```

> Review Cost: Tech Lead ~15h/sprint, Senior ~4h/sprint. Read `review_cost` from `project-config-team-detail.json`.

**Step 3 — Skill Profile + Complexity:** Read `skill_profile` from config; use complexity-adjusted throughput (see team-capacity.md) for item count limits.

**Output table:** Member | Role | Productive Hrs | Review Load | Net Available | Complexity-Adj Throughput

**🟡 REVIEW** — Present capacity table. Proceed unless user objects.

## Part B: Strategy Analysis (Phases 3-6)

> **🟢 AUTO** — Phases 3-6 delegated to `sprint-planner` agent. Escalate only on incomplete data.

```text
Agent(name: "sprint-planner"): Pass Phase 1 sprint items + Phase 2 capacity table.
Returns: Carry-over Summary + Prioritized Items + Recommended Assignments + Risk Flags.
```

### 3. Carry-over Analysis

Status-based probability model (see sprint-frameworks.md):

- >80% probability → auto-include in target sprint
- 45-80% → flag for user decision

### 4. Prioritization + Story Structure Validation

Validate stories are vertical slices (see [Sprint Frameworks](../../../references/sprint-frameworks.md#vertical-slicing)):

- [ ] End-to-end user value (not just one layer)
- [ ] Shell-only stories reframed as Walking Skeleton
- [ ] VS labels assigned (`vs{N}-{name}`, `vs-enabler`, `{feature}-{scope}`)

Priority output: P1 (high impact/low effort) → P2 (high/high) → P3 (low/low) → P4 defer. Flag unready stories — do NOT silently include.

### 5. Workload Distribution

Skill matrix match → existing context → hours capacity check → grouping. Never assign above 95% utilization.
See [references/assignment-algorithm.md](references/assignment-algorithm.md) for scoring rules.

### 6. Risk Assessment

Check all 8 dimensions:

- [ ] No member >95% utilization
- [ ] Dependencies identified; critical path items have an owner
- [ ] Junior devs have mentor support
- [ ] No one has >3 sticky carry-over items
- [ ] Bus factor areas covered (Video, DevOps, Mobile)
- [ ] Reviewer not >40% productive hours on reviews
- [ ] Cross-training opportunity flagged for bus-factor=1 areas

### 7. Risk Forecast

> **🟡 REVIEW** — Run risk-forecaster agent. If MEDIUM+ risk, ask user to apply mitigations before Phase 8.

**QG Quality Signal (🟢 AUTO — non-blocking):** Check `qg-history.jsonl` (last 30 records). If any service avg < 75% → add risk flag. Skip if file absent.

```text
Agent(name: "risk-forecaster"):
  sprint_id, sprint_name, carry_over_sp, utilization_table, p2_item_count
```

If MEDIUM+ risk: show Specific Risks + Adjusted Risk → ask "Apply mitigations? (yes/no)". If yes → apply before Phase 8.

## Part C: Approval & Execution (Phases 8-9)

### 8. Sprint Plan Review ⚠️ GATE

Present complete sprint plan:

```text
## Sprint Plan: [Sprint Name]
📅 [Start] → [End]  |  🎯 Goal: [goal]  |  📊 Velocity: [X SP]

### Team Workload
| Member | Productive Hrs | Carry-over Hrs | New Hrs | Utilization | Status |
Status: 🟢 ≤80% | ⚠️ 80-95% | 🔴 >95%

### Items (sorted by Due Date ↑ then Priority ↑)
| # | Key | Summary | Assignee | Est. Hours | Due | Priority | Action |

### Risk Summary
| Risk | Severity | Mitigation |

### Deferred Items
| Key | Summary | Reason |
```

**🔄 ITERATE** — Ask: Approve / Annotate / Major rework (max 3 rounds).

- Annotate → revise ONLY annotated items → re-present
- Approve → proceed to Phase 9
- Major rework → back to Phase 4

### 9. Execute Assignments

> **🟢 AUTO** — If Phase 8 approved → execute all. Escalate only on failure.

**Execution order:** Sort by due date (asc) then priority (Highest→Low).

```text
# Move to sprint + set estimation (sprint field = plain number, NOT object)
MCP: jira_update_issue(issue_key, additional_fields={
  "{{SPRINT_FIELD}}": 123,           # sprint ID — plain number
  "customfield_10016": 3,             # Story Points
  "customfield_10107": {"value":"M"}, # Size
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",  # Start Date
  "duedate": "YYYY-MM-DD"
})

# Subtask: NO sprint field (HR10), set estimate + dates only
MCP: jira_update_issue(issue_key, additional_fields={
  "timetracking": {"originalEstimate": "4h"},
  "{{START_DATE_FIELD}}": "YYYY-MM-DD", "duedate": "YYYY-MM-DD"
})

# Assign — use acli (MCP silently fails — HR3)
Bash: acli jira workitem assign -k "{{PROJECT_KEY}}-XXX" -a "email@domain.com" -y

# Cache invalidate after every write (HR6)
cache_invalidate(issue_key)
```

**HR8 — Post-assignment alignment (MANDATORY):**

```bash
python3 scripts/sprint/sprint_subtask_alignment.py --sprint <target_sprint_id>
# If violations → re-run with --apply to auto-fix
# Then: cache_invalidate(sprint_id=<id>)
```

**Output:**

```text
## Sprint Planning Complete ✅
Sprint: [Name] (ID: XXX) | Items assigned: XX | Team members: XX
Subtask alignment: [X checked, Y fixed]

### Execution Log (Due Date ↑ then Priority ↑)
| # | Key | Due | Priority | Action | Status |
→ To verify: /verify-issue {{PROJECT_KEY}}-XXX
```

## Options

| Flag | Description |
| `--sprint <id>` | Specify target sprint (default → next future sprint) |
| `--carry-over-only` | Phases 1-3 only — analysis without assigning |

## Examples

```text
# Good
/plan-sprint                        # interactive, resolves sprint via jira_get_sprints_from_board
/plan-sprint --sprint 47            # sprint ID from jira_get_sprints_from_board(board_id=2, state="future")
/plan-sprint --carry-over-only      # analysis-only, no moves

# Bad
/plan-sprint --sprint 47            # ❌ hardcoded without calling jira_get_sprints_from_board first (HR7)
/plan-sprint                        # ❌ without project-config-team-detail.json — capacity phase fails silently
```

**Common mistakes:** Skip capacity (Phase 2) → over-committed sprint · Hardcode sprint ID (HR7) · Set sprint on subtasks (HR10) · Use MCP assignee instead of acli (HR3) · Skip `sprint_subtask_alignment.py` post-execution (HR8)

## References

[Team Capacity](../../../references/team-capacity.md) · [Sprint Frameworks](../../../references/sprint-frameworks.md) · [Tool Selection](../../../references/tools.md) · [Pre-Meeting Checklist](references/pre-meeting-checklist.md) · [Assignment Algorithm](references/assignment-algorithm.md) · [Examples](references/examples.md)

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)
