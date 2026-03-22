---
name: blueprint-full
description: |
  Triggers: "blueprint full", "blueprint to epic", "full blueprint workflow", "blueprint ครบ"
  Orchestrates: blueprint → create-epic → create-story → verify-issue --with-subtasks
  Args: auto-detected — BEP-\d+ pattern = existing epic key; otherwise = description
model: sonnet
argument-hint: "[description] or EPIC-KEY"
---

# /blueprint-full

Orchestrates: `blueprint` → `create-epic` → `create-story` → `verify-issue --with-subtasks`

## Steps

### Step 1 — Blueprint

Auto-detect argument type from `$ARGUMENTS`:

- If matches `BEP-\d+` pattern → use as existing epic key; skip to Step 2 (epic already exists)
- Otherwise → Use the Skill tool to invoke `atlassian-pm:blueprint` with `$ARGUMENTS`

### Step 2 — Create Epic

(Skip if Step 1 used an existing epic key)
Ask: "Create epic from this blueprint?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:create-epic`
→ If no: exit after blueprint

### Step 3 — Create Story

Ask: "Create the first story now?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:create-story`
→ If no: exit

### Step 4 — Verify

Use the Skill tool to invoke `atlassian-pm:verify-issue` with `--with-subtasks`.
