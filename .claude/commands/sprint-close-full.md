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

Use the Skill tool to invoke `atlassian-pm:retrospective-analyst` (agent).
(Sprint data flows via conversation context)
