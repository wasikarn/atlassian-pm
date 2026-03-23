---
name: plan-sprint
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
description: |
  Sprint Planning using an 8-phase workflow

  Phases: Discovery → Capacity → Carry-over → Prioritize → Distribute → Risk → Review → Execute

  Triggers: "plan sprint", "sprint planning", "capacity planning", "assign work", "workload distribution", "วางแผน sprint", "จัดสรรงาน"
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
- **Recent commits:** Read from `services.tags[].path` in `project-config.json` as needed
- **Board ID:** !`python3 -c "import json,os; d=json.load(open(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), '.claude/project-config.json'))); print(d['jira']['board_id'])"`

## Pre-Meeting Checklist

> See [references/pre-meeting-checklist.md](references/pre-meeting-checklist.md) for the pre-meeting preparation checklist.

## ⚠️ Critical: Capacity Before Assignment

> Calculate team capacity BEFORE assigning individual tasks — skipping this step causes over-committed sprints and unbalanced workloads.

**Order of Operations:**

1. Calculate team velocity + individual productive hours (Phase 2)
2. Prioritize backlog items (Phase 4)
3. THEN assign to individuals using skill matrix (Phase 5)

**Anti-Pattern:** Assigning work to individuals first → leads to unbalanced sprints, burnout, missed commitments
**Anti-Pattern:** Using fixed "items/sprint" per person → ignores task complexity and skill fit

## Context Object (accumulated across phases)

| Phase | Adds to Context |
| ----- | --------------- |
| 1. Discovery | `source_sprint`, `target_sprint`, `sprint_items[]` |
| 2. Capacity | `capacity_table[]`, `available_slots[]` |
| 3. Carry-over | `carry_over_items[]`, `probability_scores[]` |
| 4. Prioritize | `prioritized_items[]`, `vs_validated` |
| 5. Distribute | `assignment_map[]`, `workload_table` |
| 6. Risk | `risk_flags[]`, `mitigations[]` |
| 6b. Risk Forecast | `risk_forecast_result`, `mitigations_applied[]` |
| 7. Review | `approved_plan` |
| 8. Execute | `execution_log[]`, `assigned_keys[]` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Part A: Data Collection (Phases 1-2) — Execution Layer

### 1. Sprint Discovery

**Goal:** Identify source and target sprints, fetch all current items with statuses, and establish the data foundation for planning.
**Required inputs:** target sprint (ask user or find next future sprint), source sprint (ask user or default to active sprint)
**Constraints:** HR7 — NEVER hardcode sprint IDs; always use `jira_get_sprints_from_board(board_id, state="future")`; REVIEW gate — present data summary before proceeding
**Output:** `source_sprint`, `target_sprint`, `sprint_items[]` with statuses, assignees, estimates, and dates

Ask the user:

- Which target sprint? (if not specified → find the next future sprint)
- Which source sprint for carry-over? (if not specified → current active sprint)

```text
MCP: jira_get_sprint_issues(sprint_id="<source>", fields="summary,status,assignee,priority,issuetype,customfield_10016,timetracking,{{START_DATE_FIELD}},duedate")
MCP: jira_get_sprint_issues(sprint_id="<target>", fields="summary,status,assignee,priority,issuetype,customfield_10016,timetracking,{{START_DATE_FIELD}},duedate")
```

**Collect:**

- Source sprint: items + statuses + assignees (carry-over candidates)
- Target sprint: existing items (already planned)
- Sprint dates + goals

**🟡 REVIEW** — Present data summary to user. Proceed unless user objects.

### 2. Team Capacity

**Goal:** Calculate each team member's net available hours and complexity-adjusted throughput for the target sprint.
**Required inputs:** `project-config.json` (members, focus_factor, throughput), `project-config-team-detail.json` (review_cost, growth_tracks, bus_factor, velocity history), leave data from user if applicable
**Constraints:** REVIEW gate — present capacity table before proceeding; do NOT assign work before this phase completes; include review load and carry-over hours before any new assignment
**Output:** `capacity_table[]` (productive hours, review load, net available, complexity-adjusted throughput per member); `available_slots[]` ready for Phase 3-5

```text
Read: ../../../references/team-capacity.md
Read: .claude/project-config.json → team.members[], team.avg_throughput_per_sprint
Read: .claude/project-config-team-detail.json → review_cost, growth_tracks, bus_factor, velocity.throughput_history
```

**Step 2a:** Team Velocity (SP-based)

```text
If velocity.story_points.avg_velocity exists:
  Sprint Capacity = avg_velocity × 0.8 (safety buffer)
Else (bootstrap phase):
  Sprint Capacity = avg_throughput_per_sprint (ticket count as proxy)

Also: sum(customfield_10016) of sprint stories → compare with Sprint Capacity to detect over-commitment
```

**Step 2b:** Individual Productive Hours

```text
Per person:
  Productive Hours = sprint_length_days × 8h × focus_factor - (leave_days × 8h × focus_factor)
  Review Load = count(reviewees) × review_cost.hours_per_junior_per_sprint  (from config)
  Already Assigned = sum(timetracking.originalEstimate) of current sprint subtasks (from Phase 1 data)
  Net Available = Productive Hours - Review Load - Already Assigned
```

> **Review Cost:** Tech Lead reviews 4 people (~15h/sprint), Senior reviews 2 (~4h/sprint).
> Read `review_cost` from `.claude/project-config-team-detail.json`.

**Step 2c:** Skill Profile + Complexity

Read each member's `skill_profile` from `project-config.json`; `growth_tracks` + `bus_factor` from `project-config-team-detail.json`.
Use **complexity-adjusted throughput** (from team-capacity.md) instead of raw throughput for item count limits.

**Output:** Capacity table

| Member | Role | Productive Hrs | Review Load | Net Available | Complexity-Adj Throughput |
| ------ | ---- | -------------- | ----------- | ------------- | ------------------------- |
| ...    | ...  | ...            | ...         | ...           | ...                      |

**🟡 REVIEW** — Present capacity table to user. Proceed unless user objects.

## Part B: Strategy Analysis (Phases 3-6)

> **🟢 AUTO** — Phases 3-6 delegated to `sprint-planner` agent. All automated. Escalate only on incomplete data.

```text
Agent(name: "sprint-planner"): Pass the following context:

## Sprint Data
[Insert Phase 1 data: source sprint items with statuses/assignees/estimates]
[Insert Phase 2 data: capacity table with productive hours per person]

The agent will:
1. Carry-over analysis (status-based probability model)
2. Prioritization (Impact/Effort matrix)
3. Workload distribution (skill match + hours capacity)
4. Risk assessment (overloads, gaps, dependencies)

Returns: Carry-over Summary + Prioritized Items + Recommended Assignments + Risk Flags tables.
```

### 3. Carry-over Analysis

**Goal:** Identify which source sprint items are likely to carry over and determine their probability scores for inclusion in target sprint planning.
**Required inputs:** `sprint_items[]` from Phase 1 (source sprint items with statuses)
**Constraints:** AUTO (delegated to sprint-planner agent); high-probability items (>80%) auto-include; medium-probability (45-80%) flag for user decision
**Output:** `carry_over_items[]`, `probability_scores[]`; carry-over count per person; high/medium item classification

**Input:** Source sprint items with statuses
**Method:** Status-based probability model (from sprint-frameworks.md)

- Estimated carry-over count per person
- High-probability items (>80%) → auto-include in target sprint
- Medium-probability items (45-80%) → flag for user decision

### 4. Prioritization + Story Structure Validation

**Goal:** Order target sprint items by business value and validate that each story delivers a true vertical slice.
**Required inputs:** target sprint items + new items to add (from Phase 1), carry-over items (from Phase 3)
**Constraints:** AUTO (delegated to sprint-planner agent); Definition of Ready must pass — flag unready stories, do NOT silently include them; VS labels required
**Output:** `prioritized_items[]` (P1-P4 classification), `vs_validated`; unready stories flagged with reason

**Validate stories are vertical slices** (see [Sprint Frameworks](../../../references/sprint-frameworks.md#vertical-slicing)):

- [ ] Each story delivers end-to-end user value (not just one layer)
- [ ] Shell-only stories reframed as Walking Skeleton
- [ ] VS labels assigned (`vs{N}-{name}`, `vs-enabler`, `{feature}-{scope}`)

**Input:** Target sprint items + new items to add
**Method:** Impact vs Effort matrix

**Output:**

- P1 (DO FIRST): High impact, low effort
- P2 (PLAN CAREFULLY): High impact, high effort
- P3 (QUICK WINS): Low impact, low effort
- P4 (DEFER): Low impact, high effort

### 5. Workload Distribution

**Goal:** Assign each prioritized item to the best-fit team member without exceeding individual capacity.
**Required inputs:** `prioritized_items[]` from Phase 4, `capacity_table[]` from Phase 2, `carry_over_items[]` from Phase 3, skill profiles from `project-config.json`
**Constraints:** AUTO (delegated to sprint-planner agent); never assign above 95% utilization; use skill matrix match → context → hours capacity order; see assignment-algorithm.md for scoring rules
**Output:** `assignment_map[]`, `workload_table` with hours tracking per member

**Input:** Prioritized items + team capacity (hours) + carry-over + skill profiles
**Method:** Skill matrix match → existing context → hours capacity check → grouping

> See [references/assignment-algorithm.md](references/assignment-algorithm.md) for the detailed skill-match scoring algorithm and assignment rules.

### 6. Risk Assessment

**Goal:** Identify capacity overloads, dependency gaps, bus factor exposures, and review load issues before the plan is approved.
**Required inputs:** `assignment_map[]` from Phase 5, `capacity_table[]` from Phase 2, bus_factor data from `project-config-team-detail.json`
**Constraints:** AUTO (delegated to sprint-planner agent); check all 8 risk dimensions listed below; if any member >95% utilization → remove an item, do not redistribute
**Output:** `risk_flags[]` with severity + mitigation per flag; ready for Phase 6b risk-forecaster

**Check:**

- [ ] No one exceeds capacity ceiling (utilization >95%)
- [ ] Dependencies identified
- [ ] Critical path items have an owner
- [ ] Junior devs have mentor support
- [ ] No one has >3 sticky carry-over items
- [ ] Bus factor areas covered (Video Processing, DevOps, Mobile → check if sole owner is overloaded or on leave)
- [ ] Review load validated (reviewer not >40% of productive hours on reviews)
- [ ] Cross-training opportunity flagged (if sprint items touch bus-factor=1 areas → suggest pairing)

**Output:** Risk flags with severity + mitigation

### 6b. Risk Forecast (risk-forecaster agent)

**Goal:** Apply the risk-forecaster agent to quantify sprint risk level and produce adjusted mitigations before plan approval.
**Required inputs:** `risk_flags[]` from Phase 6, sprint-planner output (carry_over_sp, utilization_table, p2_item_count), QG history (optional)
**Constraints:** REVIEW gate — present risk forecast findings; if MEDIUM or higher risk, ask user whether to apply mitigations before proceeding to Phase 7
**Output:** `risk_forecast_result`, `mitigations_applied[]`; sprint changes applied if user accepts mitigations

> **🟡 REVIEW** — Run risk-forecaster with sprint-planner output. Present findings. Proceed unless user objects.

**QG Quality Signal (🟢 AUTO — non-blocking):**

Before dispatching risk-forecaster, check spec quality history:

```bash
python -c "
import json, os
from pathlib import Path
data_dir = Path(os.environ.get('CLAUDE_PLUGIN_DATA', Path.home() / '.claude' / 'plugins' / 'data' / 'atlassian-pm-atlassian-pm'))
qg_file = data_dir / 'qg-history.jsonl'
if not qg_file.exists():
    print('No QG history yet.')
else:
    records = [json.loads(l) for l in qg_file.read_text().splitlines() if l.strip()][-30:]
    from collections import defaultdict
    by_service = defaultdict(list)
    for r in records:
        if r.get('service'):
            by_service[r['service']].append(r['score'])
    for svc, scores in sorted(by_service.items()):
        avg = sum(scores) / len(scores)
        print(f'{svc}: avg={avg:.0f}% ({len(scores)} records)')
"
```

If any service tag has avg QG score < 75% across last 30 records → add to risk flags: "Spec quality signal: `[SERVICE]` stories have low avg QG score (XX%) — subtasks in this sprint may need extra review before coding starts."
If `qg-history.jsonl` does not exist → skip this step.

```text
Agent(name: "risk-forecaster"):
  sprint_id: [sprint_id from lookup]
  sprint_name: [sprint_name]
  carry_over_sp: [carry-over SP total from sprint-planner output]
  utilization_table: [member utilization% from sprint-planner Recommended Assignments table]
  p2_item_count: [count of P2 items from sprint-planner Prioritized Items table]
```

Present the Risk Forecast to user. If MEDIUM or higher risk:

- Show Specific Risks section
- Show Adjusted Risk if mitigations applied
- Ask: "Apply recommended mitigations before finalizing? (yes/no)"

If user accepts mitigations → apply sprint changes (remove items, add pairing notes) before proceeding to Phase 7.

## Part C: Approval & Execution (Phases 7-8) — Execution Layer

### 7. Sprint Plan Review ⚠️ GATE

**Goal:** Get explicit user approval on the complete sprint plan (workload, assignments, risks, deferred items) before executing any Jira writes.
**Required inputs:** all context from Phases 1-6b: capacity table, prioritized items, assignment map, risk flags, mitigations
**Constraints:** ITERATE gate — max 3 annotation rounds; annotate → revise ONLY annotated items; major rework returns to Phase 4; do NOT execute assignments without APPROVE
**Output:** `approved_plan`; user has confirmed sprint goal, assignments, and risk mitigations

Present the complete sprint plan to the user:

```text
## Sprint Plan: [Sprint Name]
📅 [Start Date] → [End Date]
🎯 Sprint Goal: [goal]
📊 Team Velocity: [X SP or Y tickets] (based on last 3-5 sprints)

### Team Workload (Hours-Based)
| Member | Role | Productive Hrs | Carry-over Hrs | New Hrs | Total Hrs | Utilization | Status |
| ... | ... | ... | ... | ... | ... | ...% | 🟢/⚠️/🔴 |

Status: 🟢 ≤80% | ⚠️ 80-95% | 🔴 >95%

### Items to Assign (sorted by Due Date ↑ then Priority ↑)
| # | Key | Summary | Assignee | Skill Match | Est. Hours | Due Date | Priority | Action |
| 1 | {{PROJECT_KEY}}-XXX | ... | Name | expert | 4h | Feb 10 | Highest | assign + move |

### Risk Summary
| Risk | Severity | Mitigation |

### Deferred Items (not included in this sprint)
| Key | Summary | Reason |
```

**🔄 ITERATE** — Present complete sprint plan as structured cards (workload per member, item assignments, risk flags). Ask: Approve / Annotate / Major rework.

- Annotate → user specifies items to reassign, adjust hours, swap priorities → revise ONLY annotated items → re-present (max 3 rounds)
- Approve → proceed to Execute Assignments
- Major rework → back to Prioritization (Phase 4)
- See [Annotation Cycle](../../../references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 8. Execute Assignments

**Goal:** Apply the approved sprint plan to Jira — move items to target sprint, set estimation fields, assign team members, and run post-assignment alignment validation.
**Required inputs:** `approved_plan` from Phase 7, sprint ID from `jira_get_sprints_from_board()` lookup
**Constraints:** HR7 — sprint ID must be looked up dynamically, NEVER hardcoded; HR10 — NEVER set sprint field on subtasks; HR3 — use acli for assignee (MCP silently fails); HR6 — `cache_invalidate` after every write; HR8 — run `sprint_subtask_alignment.py` post-execution (mandatory); execute in due date + priority order
**Output:** `execution_log[]`, `assigned_keys[]`; subtask alignment check passed; sprint planning complete

> **🟢 AUTO** — If Phase 7 approved → execute all assignments automatically. Escalate only on failure.
> HR7: Sprint ID must be looked up dynamically. NEVER hardcode sprint IDs.

**Execution Order:** Sort items by due date (ascending) then priority (Highest→Low). This ensures critical early-due items are assigned first.

Execute according to the user-approved plan (in due date + priority order):

```text
# Move items to target sprint + set estimation fields (⚠️ sprint field = plain number, NOT object)
# Story/Task: set sprint + story_points + size + dates
MCP: jira_update_issue(issue_key="{{PROJECT_KEY}}-XXX", additional_fields={
  "{{SPRINT_FIELD}}": 123,
  "customfield_10016": 3,                        # Story Points
  "customfield_10107": {"value": "M"},            # Size
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",              # Start Date
  "duedate": "YYYY-MM-DD"                         # Due Date
})

# Subtask: set original_estimate + dates (⚠️ HR10: NEVER set sprint on subtasks)
MCP: jira_update_issue(issue_key="{{PROJECT_KEY}}-YYY", additional_fields={
  "timetracking": {"originalEstimate": "4h"},     # Original Estimate
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",              # Start Date
  "duedate": "YYYY-MM-DD"                         # Due Date
})

# Assign items (⚠️ MCP assignee silent fail — use acli instead)
Bash: acli jira workitem assign -k "{{PROJECT_KEY}}-XXX" -a "email@domain.com" -y
```

> ⚠️ Sprint field uses `{{SPRINT_FIELD}}` with plain number (e.g. `123`) — do not use `{"id": 123}`
> **🟢 AUTO** — HR3: NEVER set assignee via MCP. Use `acli jira workitem assign -k "KEY" -a "email" -y`.
> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after EVERY sprint assignment.

**HR8 — Post-assignment alignment check (MANDATORY):**

```text
# After all assignments complete, run subtask alignment validation:
Bash: python3 scripts/sprint/sprint_subtask_alignment.py --sprint <target_sprint_id>

# Reviews: dates within parent range, missing OE, missing dates
# If violations found → run with --apply to auto-fix
# Then cache_invalidate(sprint_id=<id>) to refresh cache
```

> **🟢 AUTO** — Always run alignment check after Phase 8. This is the safety net for HR8.

**Output:**

```text
## Sprint Planning Complete ✅
Sprint: [Name] (ID: XXX)
Items assigned: XX
Team members: XX
Subtask alignment: [X checked, Y fixed]

### Execution Log (ordered by Due Date ↑ then Priority ↑)
| # | Key | Due | Priority | Action | Status |
| 1 | {{PROJECT_KEY}}-XXX | Feb 10 | Highest | Assigned to Name + moved to sprint | ✅ |

→ To verify: /verify-issue {{PROJECT_KEY}}-XXX
→ To update a story: /update-story {{PROJECT_KEY}}-XXX
```

## Options

| Flag | Description |
| ------ | ------------- |
| `--sprint <id>` | Specify target sprint ID (if not specified → find the next future sprint) |
| `--carry-over-only` | Carry-over analysis only (no assign/move) — Phase 1-3 only |

## Example

> See [references/examples.md](references/examples.md) for a full sprint planning input/output example.

## Examples

### ✅ Good

```text
/plan-sprint                                  # interactive — resolves next future sprint via jira_get_sprints_from_board
/plan-sprint --sprint 47                      # sprint ID from jira_get_sprints_from_board(board_id={{BOARD_ID}}, state="future")
/plan-sprint --carry-over-only                # analysis-only — review carry-over candidates without assigning or moving
/plan-sprint --sprint 47 --carry-over-only    # carry-over analysis for a specific future sprint
```

### ❌ Bad

```text
/plan-sprint --sprint 47              # ❌ sprint ID hardcoded without calling jira_get_sprints_from_board first (HR7)
/plan-sprint                          # ❌ run without project-config-team-detail.json present — capacity phase will fail silently
/plan-sprint --carry-over-only        # ❌ wrong flag when full planning (assign + move) is needed — use without flag
/close-sprint                         # ❌ wrong skill — /close-sprint ends a sprint; /plan-sprint plans the next one
```

**Common mistakes:**

- Skipping capacity calculation (Phase 2) and jumping straight to assignments — leads to over-committed sprints and ignored skill fit
- Hardcoding a sprint ID instead of calling `jira_get_sprints_from_board(board_id={{BOARD_ID}}, state="future")` (HR7 violation)
- Setting the sprint field (`{{SPRINT_FIELD}}`) on subtasks during Phase 8 — subtasks inherit sprint from parent (HR10)
- Using `acli` or MCP assignee field directly instead of `acli jira workitem assign -k KEY -a email -y` (HR3 — MCP assignee silently fails)
- Not running `sprint_subtask_alignment.py` after execution — skipping the mandatory HR8 post-assignment check

## References

- [Team Capacity](../../../references/team-capacity.md) - Capacity formulas, skill matrix, thresholds (roster data in project-config.json)
- [Sprint Frameworks](../../../references/sprint-frameworks.md) - RICE, Impact/Effort, carry-over model
- [Tool Selection](../../../references/tools.md) - MCP vs acli decision rules
- [Pre-Meeting Checklist](references/pre-meeting-checklist.md)
- [Assignment Algorithm](references/assignment-algorithm.md)
- [Examples](references/examples.md)

## 🎓 Domain Expert Notes

### Why This Approach

The Scrum Guide 2020 defines Sprint Planning as answering three questions: Why is this Sprint valuable? What can be Done? How will the chosen work get done? This skill's 8-phase flow maps directly to those questions — capacity (Phase 2) answers "what can be Done," prioritization (Phase 4) answers "what is valuable," and distribution + risk (Phases 5-6) answer "how." Skipping any phase degrades the quality of the answer to its corresponding question.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Scrum Guide 2020 Sprint Planning | Phases 1-8 overall structure | The authoritative definition of what Sprint Planning must produce: a Sprint Goal + Sprint Backlog + execution plan |
| Yesterday's Weather (Scrum pattern) | Phase 2 — team velocity calculation | Plan at 80% of 3-sprint rolling average velocity; single-sprint data is noise; ±20% is the reliable precision band |
| Definition of Ready (DoR) | Phase 4 — story readiness validation | A PBI is ready for planning only when it has: clear acceptance criteria, estimated size, no unresolved dependencies, and approved design/mockups; items failing DoR should be returned to refinement, not planned |
| Impact/Effort Matrix (2×2) | Phase 4 — prioritization | P1 (high impact, low effort) items are the sprint's non-negotiables; P4 (low impact, high effort) items should be explicitly deferred with a written reason in Jira |
| Focus Factor (capacity model) | Phase 2 individual capacity | Industry benchmark: 0.6–0.7 for most developers; <0.5 signals meeting overload or context switching — investigate before sprint starts |
| SMART Sprint Goals | Phase 7 review | Sprint Goals must be Specific (names the value), Measurable (has a done signal), Achievable (fits capacity), Relevant (aligned to product goal), Time-bound (sprint end = deadline) |

### Key Metrics

- **Team Velocity (rolling 3-sprint avg):** the primary planning input — use 80% of this as the sprint capacity ceiling to build in a safety buffer
- **Individual Utilization %:** (assigned hours / net available hours) × 100 — healthy: 70-85%; >95% = no slack for impediments, almost always results in carry-over
- **Carry-over Probability Score:** based on status at planning time — In Progress >80% = high carry-over likelihood; To Do <45% = genuinely new capacity
- **Bus Factor Coverage:** count of sprint items that only one person can complete — any bus factor = 1 area should have a designated backup or pairing plan before sprint starts
- **Review Load Ratio:** (review hours / productive hours) × 100 — Tech Lead >40% signals too many direct reports to review; creates bottleneck at PR stage

### Expert Decision Criteria

- **If a story has no sprint goal alignment:** don't plan it — ask the Product Owner to articulate which sprint goal this contributes to; "nice to have" is not a sprint goal
- **If carry-over probability >80% for 3+ items from prior sprint:** do not plan new P2 items — resolve the carry-over backlog first; new items will also carry over
- **If utilization exceeds 85% for any member after distribution:** remove one item, not redistribute — adding pressure to an already-full schedule does not reduce carry-over risk
- **If Definition of Ready fails on a story:** flag in Phase 4, do not silently include it — planning an unready story is the single largest source of mid-sprint scope confusion
- **If sprint has no clear, singular sprint goal:** the sprint is a feature factory, not a Scrum sprint — push back and ask the Product Owner to identify the one outcome this sprint advances

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Sprint over-committed every time | Capacity calculated in items/sprint, not hours | Switch to focus-factor-adjusted hours; include review load and carry-over hours before any new assignment |
| Team splits on estimation during planning | No shared Definition of Done; different complexity models | Run one round of planning poker on a reference story before starting; anchor the team's scale |
| Sprint goal too vague ("continue features") | Product Owner hasn't defined value increment | Require SMART goal format; reject "continue" goals — they make sprint success unmeasurable |
| Junior devs consistently under-deliver | Items assigned beyond skill level without pairing | Match skill_profile to task complexity; add pairing note in the Jira issue for any task assigned 1 level above DoR |
| Subtask dates outside parent range (HR8 violations) | Subtask estimates set independently from parent | Always run `sprint_subtask_alignment.py` post-execution; it is the HR8 safety net |

### Authoritative References

- **Scrum Guide 2020 (Sutherland/Schwaber):** Sprint Planning is timeboxed to 8 hours for a one-month sprint. "The Sprint Goal, the Product Backlog items selected for the Sprint, plus the plan for delivering them are together referred to as the Sprint Backlog."
- **Scrum Patterns — Yesterday's Weather (Coplien/Harrison):** "Teams that plan to their recent actual velocity consistently outperform teams that plan to theoretical capacity by 25-40% in delivery predictability."
- **Roman Pichler — Definition of Ready:** "Using a DoR helps teams avoid pulling in items that are not sufficiently understood, thereby reducing the risk of incomplete work and carry-over."
