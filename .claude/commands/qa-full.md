---
name: qa-full
description: |
  Triggers: "qa full", "create and run testplan", "QA end-to-end", "ทดสอบ story ครบ", "QA ครบ"
  Orchestrates: create-testplan → execute-testplan
model: sonnet
argument-hint: "<issue-key> [--env staging|production]"
---

# /qa-full

Orchestrates: `create-testplan` → `execute-testplan`

## Steps

### Step 1 — Create Test Plan

Use the Skill tool to invoke `atlassian-pm:create-testplan` with `$ARGUMENTS`.
→ Produces [QA] Sub-task with embedded test plan linked to the story.
→ Wait for skill to complete and confirm [QA] Sub-task key (e.g., {{PROJECT_KEY}}-XXXX).

### Step 2 — Confirm Execute

Ask: "Test plan created. Run execute-testplan against **staging** now?"
→ If yes (or no --env specified): proceed with `--env staging`
→ If user specifies `--env production`: warn "⚠️ Running against production — confirm?" before proceeding
→ If no: exit after test plan creation

### Step 3 — Execute Test Plan

Use the Skill tool to invoke `atlassian-pm:execute-testplan` with the issue key from `$ARGUMENTS` and resolved `--env` flag.
→ Results written back to Google Sheet, bugs created for failures, summary posted to Jira.
