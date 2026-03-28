---
name: story-analyze-full
description: |
  Triggers: "analyze story full", "analyze and verify", "วิเคราะห์ story ครบ"
  Orchestrates: analyze-story → verify-issue --with-subtasks
model: sonnet
argument-hint: "ISSUE-KEY"
---

# /story-analyze-full

Orchestrates: `analyze-story` → `verify-issue --with-subtasks`

## Steps

### Step 1 — Analyze Story

Use the Skill tool to invoke `atlassian-pm:analyze-story` with `$ARGUMENTS` (issue key).

### Step 2 — Verify

> **Gate:** Confirm Step 1 produced an analysis output (not an error). If analyze-story reported a fetch failure or missing issue, STOP — there is nothing to verify.

Use the Skill tool to invoke `atlassian-pm:verify-issue` with `$ARGUMENTS --with-subtasks`.
