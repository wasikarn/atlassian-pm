---
name: sprint-close-full
description: |
  Triggers: "close sprint full", "end sprint complete", "sprint closure with retro", "ปิด sprint ครบ"
  Orchestrates: close-sprint → retrospective-analyst
model: sonnet
argument-hint: "[--sprint SPRINT-ID]"
---

# /sprint-close-full

Orchestrates: `close-sprint` → `retrospective-analyst`

## Steps

### Step 1 — Close Sprint

Use the Skill tool to invoke `atlassian-pm:close-sprint` with `$ARGUMENTS`.

### Step 2 — Retrospective

> **Gate:** Confirm Step 1 completed successfully (sprint is closed, sprint ID is known). If close-sprint reported an error or no sprint was found, STOP — retrospective requires a completed sprint.

Dispatch the `atlassian-pm:retrospective-analyst` agent to generate the retrospective analysis.
(Sprint data from Step 1 flows via conversation context — pass it explicitly in the agent prompt)
