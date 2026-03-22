---
name: story-full
description: |
  Triggers: "story full", "create story end-to-end", "new story complete", "สร้าง story ครบ"
  Orchestrates: search-issues → create-story → verify-issue --with-subtasks
model: sonnet
argument-hint: "[story-description]"
---

# /story-full

Orchestrates: `search-issues` → `create-story` → `verify-issue --with-subtasks`

## Steps

### Step 1 — Dedup Check

Use the Skill tool to invoke `atlassian-pm:search-issues` with `$ARGUMENTS` as the search query.
→ If a duplicate is found: show the existing issue key and ask — "Duplicate found: [KEY]. Proceed anyway or stop?"
→ If stop: exit and show the duplicate key to the user

### Step 2 — Create Story

Use the Skill tool to invoke `atlassian-pm:create-story` with `$ARGUMENTS`.
The story_key flows via conversation context — no explicit passing needed.

### Step 3 — Verify

Use the Skill tool to invoke `atlassian-pm:verify-issue` with the story key from conversation context and `--with-subtasks`.
