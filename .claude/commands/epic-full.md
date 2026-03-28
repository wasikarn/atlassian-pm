---
name: epic-full
description: |
  Triggers: "epic full", "create epic end-to-end", "epic with story", "สร้าง epic ครบ"
  Orchestrates: search-issues → create-epic → create-story → verify-issue --with-subtasks
model: sonnet
context: fork
argument-hint: "[epic-description]"
---

# /epic-full

Orchestrates: `search-issues` → `create-epic` → `create-story` → `verify-issue --with-subtasks`

## Steps

### Step 1 — Dedup Check

Use the Skill tool to invoke `atlassian-pm:search-issues` with `$ARGUMENTS`.
→ If duplicate found: ask user — "Similar epic exists: [KEY]. Proceed anyway or stop?"
→ If stop: exit

### Step 2 — Create Epic

Use the Skill tool to invoke `atlassian-pm:create-epic` with `$ARGUMENTS`.
Epic key flows via conversation context.

### Step 3 — Create First Story

> **Gate:** Confirm Step 2 produced an epic key (`[A-Z]+-\d+`). If create-epic failed or was aborted, STOP and show: "create-epic did not complete — resolve before creating a story."

Ask: "Create the first story for this epic now?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:create-story` linked to the new epic
→ If no: exit after epic creation

### Step 4 — Verify

> **Gate:** Only proceed if Step 2 produced an epic key AND (Step 3 was skipped by user choice OR create-story produced a story key). If create-story was invoked but failed, STOP.

Use the Skill tool to invoke `atlassian-pm:verify-issue` with the epic key from conversation context and `--with-subtasks`.
