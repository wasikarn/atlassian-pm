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

Ask: "Map dependencies for this sprint now?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:map-dependencies`
→ If no: exit after sprint planning
(Sprint context flows from conversation — no explicit passing needed)
