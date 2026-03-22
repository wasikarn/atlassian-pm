---
name: epic-full
description: |
  Triggers: "epic full", "create epic end-to-end", "epic with story", "สร้าง epic ครบ"
  Orchestrates: search-issues → create-epic → create-story → verify-issue --with-subtasks
model: sonnet
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

Ask: "Create the first story for this epic now?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:create-story` linked to the new epic
→ If no: exit after epic creation

### Step 4 — Verify

Use the Skill tool to invoke `atlassian-pm:verify-issue` with the epic key `--with-subtasks`.
