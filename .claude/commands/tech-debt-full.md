---
name: tech-debt-full
description: |
  Triggers: "tech debt full", "scan and create tasks", "tech debt end-to-end", "จัดการ tech debt ครบ"
  Orchestrates: scan-tech-debt → create-task (per selected item)
model: sonnet
argument-hint: "[--update]"
---

# /tech-debt-full

Orchestrates: `scan-tech-debt` → `create-task` (per selected item)

## Steps

### Step 1 — Scan Tech Debt

Use the Skill tool to invoke `atlassian-pm:scan-tech-debt` with `$ARGUMENTS`.
A list of tech debt items is produced.

### Step 2 — Select Items

Ask: "Which items should I create tasks for? (list numbers, 'all', or 'none')"
→ If none: exit
→ If selection: proceed to Step 3 for each selected item

### Step 3 — Create Tasks

For each selected item, use the Skill tool to invoke `atlassian-pm:create-task`.
(Pass each item's title and description from scan output via conversation context)
