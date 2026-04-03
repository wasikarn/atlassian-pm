---
name: epic-health
context: fork
agent: general-purpose
effort: medium
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian]
argument-hint: "[epic-key]"
description: |
  This skill should be used when auditing an epic before sprint or release cutoff. Analyzes task coverage, SP totals, timeline feasibility, and AC alignment.
  
  Checks:
  - All tasks linked to epic with SP estimates
  - SP sum is realistic vs team velocity
  - Tasks cover all epic objectives (no blind spots)
  - No tasks missing QG verification
  - Timeline: estimated completion vs target date
  
  Trigger phrases: "epic health", "check epic", "epic status", "epic audit", "sprint readiness", "วิเคราะห์ epic", "ตรวจ epic"
  
  This skill should NOT be used for creating issues (use create-task) or updating epic fields (use update-epic).
allowed-tools: mcp__atlassian-cache__cache_get_issue, mcp__atlassian-cache__cache_search, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__jira_get_sprints_from_board
---

# Epic Health Analysis

## Phase 1: Load Epic Data

1. Fetch the epic via `cache_get_issue` first, fallback to `jira_get_issue`.
2. Fetch all linked tasks. Use JQL (NO ORDER BY per HR2):
   - `"Epic Link" = <epic-key>` or `parent = <epic-key>`
3. For each task, collect: status, SP estimate, AC count, assignee, sprint.

## Phase 2: Health Checks

Run all checks in parallel:

### 🔍 Coverage Check

- Do the tasks collectively cover all objectives in the epic description?
- Flag any epic objectives that have no corresponding task.

### 📊 Estimation Check

- Sum SP across all stories (exclude Done stories if sprint is in-flight).
- Compare to team velocity if available (project-config-team-detail.json).
- Flag: total SP > 3× velocity = likely multi-sprint, needs breakdown confirmation.

### ✅ Completeness Check

- Tasks with no SP estimate → flag
- Tasks with no AC → flag
- Tasks not linked to any sprint (status not Backlog) → flag

### 📅 Timeline Check

- If epic has a target date (`duedate`): estimate completion date based on velocity.
- Flag if estimated completion > target date.

## Phase 3: Health Report

Present a structured report:

```
Epic: <KEY> — <Summary>

Overall Health: 🟢 Healthy / 🟡 At Risk / 🔴 Critical

Issues Found:
  [Coverage]   <list>
  [Estimation] <list>
  [Readiness]  <list>
  [Timeline]   <list>

Recommended Actions:
  1. <action>
  2. <action>
```

Set health to:

- 🟢 Healthy: 0 issues
- 🟡 At Risk: 1–3 minor issues or 1 major issue
- 🔴 Critical: multiple major issues or missed timeline

## 🎓 Domain Expert Notes

See [references/health-criteria.md](references/health-criteria.md) for health check thresholds, scoring formulas, and example outputs.

## References

[Health Criteria](references/health-criteria.md) · [Workflow Patterns](../../../references/workflow-patterns.md)
