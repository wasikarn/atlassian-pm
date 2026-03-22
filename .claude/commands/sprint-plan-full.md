---
name: sprint-plan-full
description: |
  Triggers: "sprint plan full", "plan sprint complete", "plan sprint with dependencies", "วางแผน sprint ครบ"
  Orchestrates: plan-sprint → map-dependencies
model: sonnet
argument-hint: "[--sprint SPRINT-ID]"
---

# /sprint-plan-full

Orchestrates: `plan-sprint` → `map-dependencies`

## Steps

### Step 1 — Plan Sprint

Use the Skill tool to invoke `atlassian-pm:plan-sprint` with `$ARGUMENTS`.

### Step 2 — Map Dependencies

Use the Skill tool to invoke `atlassian-pm:map-dependencies`.
(Uses the sprint from conversation context — no explicit passing needed)
