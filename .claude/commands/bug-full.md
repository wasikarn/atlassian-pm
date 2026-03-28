---
name: bug-full
description: |
  Triggers: "bug full", "bug triage complete", "report bug end-to-end", "รายงาน bug ครบ"
  Orchestrates: search-issues → bug-triage → create-testplan
model: sonnet
argument-hint: "[bug-description]"
---

# /bug-full

Orchestrates: `search-issues` → `bug-triage` → `create-testplan`

## Steps

### Step 1 — Dedup Check

Use the Skill tool to invoke `atlassian-pm:search-issues` with `$ARGUMENTS`.
→ If existing bug found: ask user — "Similar bug exists: [KEY]. Proceed anyway or stop?"
→ If stop: exit

### Step 2 — Bug Triage

Use the Skill tool to invoke `atlassian-pm:bug-triage` with `$ARGUMENTS`.
Bug issue key flows via conversation context.

### Step 3 — Create Test Plan

> **Gate:** Confirm Step 2 produced a bug issue key. If bug-triage failed or was aborted without a key, STOP and show: "bug-triage did not complete — resolve before creating a test plan."

Ask: "Create a test plan for this bug?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:create-testplan`
→ If no: exit after triage
