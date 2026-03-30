---
name: vibe-full
description: |
  Triggers: "vibe full", "idea to tasks", "feature end-to-end vibe", "สร้าง feature ครบ vibe"
  Orchestrates: search-issues → vibe-plan → verify-issue --with-subtasks
model: sonnet
argument-hint: "[feature-description]"
---

# /vibe-full

Orchestrates: `search-issues` → `vibe-plan` → `verify-issue --with-subtasks`

## Steps

### Step 1 — Dedup Check

Use the Skill tool to invoke `atlassian-pm:search-issues` with `$ARGUMENTS` as the search query.
→ If a duplicate is found: show the existing issue key and ask — "Duplicate found: [KEY]. Proceed anyway or stop?"
→ If stop: exit and show the duplicate key to the user

### Step 2 — Vibe Plan

**Circuit breaker:** Before invoking vibe-plan, check conversation history for a completed epic key (pattern `[A-Z]+-\d+` from a previous vibe-plan run in this session). If found, ask:

> "Epic [KEY] was already created in this session. Skip to Step 3 (verify) or restart from scratch?"
> → Skip: proceed to Step 3 with that key
> → Restart: invoke vibe-plan again (warn that duplicates may be created)

Use the Skill tool to invoke `atlassian-pm:vibe-plan` with `$ARGUMENTS`.
The epic_key and story_keys flow via conversation context — no explicit passing needed.

### Step 3 — Verify

> **Gate:** Confirm Step 2 produced an epic key (`[A-Z]+-\d+` in conversation context). If vibe-plan failed or was aborted without a key, STOP and show: "vibe-plan did not complete — resolve before verifying."

For each story key created in Step 2, use the Skill tool to invoke `atlassian-pm:verify-issue` with the story key and `--with-subtasks`.
