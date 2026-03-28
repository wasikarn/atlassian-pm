---
name: epic-health
disable-model-invocation: true
context: fork
agent: general-purpose
effort: medium
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian]
argument-hint: "[epic-key]"
description: |
  Analyze epic health: story coverage, SP totals, timeline feasibility, and AC alignment.

  Checks:
  - All stories linked to epic with SP estimates
  - SP sum is realistic vs team velocity
  - Stories cover all epic objectives (no blind spots)
  - No stories missing QG verification
  - Timeline: estimated completion vs target date

  Triggers: "epic health", "check epic", "epic status", "วิเคราะห์ epic", "ตรวจ epic"
  Use when: auditing an epic before a sprint or release cutoff
allowed-tools: mcp__atlassian-cache__cache_get_issue, mcp__atlassian-cache__cache_search, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__jira_get_sprints_from_board
---

# Epic Health Analysis

## Phase 1: Load Epic Data

1. Fetch the epic via `cache_get_issue` first, fallback to `jira_get_issue`.
2. Fetch all linked stories. Use JQL (NO ORDER BY per HR2):
   - `"Epic Link" = <epic-key>` or `parent = <epic-key>`
3. For each story, collect: status, SP estimate, AC count, assignee, sprint.

## Phase 2: Health Checks

Run all checks in parallel:

### 🔍 Coverage Check

- Do the stories collectively cover all objectives in the epic description?
- Flag any epic objectives that have no corresponding story.

### 📊 Estimation Check

- Sum SP across all stories (exclude Done stories if sprint is in-flight).
- Compare to team velocity if available (project-config-team-detail.json).
- Flag: total SP > 3× velocity = likely multi-sprint, needs breakdown confirmation.

### ✅ Completeness Check

- Stories with no SP estimate → flag
- Stories with no AC → flag
- Stories not linked to any sprint (status not Backlog) → flag

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
