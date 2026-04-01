---
name: blueprint-full
description: |
  Triggers: "blueprint full", "blueprint to epic", "full blueprint workflow", "blueprint ครบ"
  Orchestrates: blueprint → create-epic → create-task → verify-issue
  Args: auto-detected — [A-Z]+-\d+ pattern = existing epic key; otherwise = description
model: sonnet
context: fork
argument-hint: "[description] or EPIC-KEY"
---

# /blueprint-full

Orchestrates: `blueprint` → `create-epic` → `create-task` → `verify-issue`

## Steps

### Step 1 — Blueprint

Auto-detect argument type from `$ARGUMENTS`:

- If matches `[A-Z]+-\d+` pattern → use as existing epic key; skip to Step 3 (epic already exists, no need to create)
- Otherwise → Use the Skill tool to invoke `atlassian-pm:blueprint` with `$ARGUMENTS`

### Step 2 — Create Epic

(Skip if Step 1 used an existing epic key)
Ask: "Create epic from this blueprint?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:create-epic`
→ If no: exit after blueprint

### Step 3 — Create Task

> **Gate:** Confirm an epic key is present in conversation context (either from Step 1 existing key or Step 2 create-epic output). If no epic key, STOP and show: "No epic key available — cannot create a task without a parent epic."

Ask: "Create the first task now?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:create-task`
→ If no: exit

### Step 4 — Verify

> **Gate:** Only proceed if create-task was invoked AND produced a task key. If task creation was skipped (user said No), run verify on the epic key instead. If create-task failed, STOP.

Use the Skill tool to invoke `atlassian-pm:verify-issue` with the created key.
