---
name: task-full
description: |
  Triggers: "task full", "create task end-to-end", "new task complete", "สร้าง task ครบ"
  Orchestrates: search-issues → create-task → verify-issue
model: sonnet
argument-hint: "[task-description]"
---

# /task-full

Orchestrates: `search-issues` → `create-task` → `verify-issue`

## Steps

### Step 1 — Dedup Check

Use the Skill tool to invoke `atlassian-pm:search-issues` with `$ARGUMENTS` as the search query.
→ If a duplicate is found: show the existing issue key and ask — "Duplicate found: [KEY]. Proceed anyway or stop?"
→ If stop: exit and show the duplicate key to the user

### Step 2 — Create Task

**Circuit breaker:** Before invoking create-task, check conversation history for a completed task key (pattern `[A-Z]+-\d+` from a previous create-task run in this session). If found, ask:

> "Task [KEY] was already created in this session. Skip to Step 3 (verify) or restart from scratch?"
> → Skip: proceed to Step 3 with that key
> → Restart: invoke create-task again (warn that a duplicate may be created)

Use the Skill tool to invoke `atlassian-pm:create-task` with `$ARGUMENTS`.
The task_key flows via conversation context — no explicit passing needed.

### Step 3 — Verify

> **Gate:** Confirm Step 2 produced a task key (`[A-Z]+-\d+` in conversation context). If create-task failed or was aborted without a key, STOP and show: "create-task did not complete — resolve before verifying."

Use the Skill tool to invoke `atlassian-pm:verify-issue` with the task key from conversation context.
