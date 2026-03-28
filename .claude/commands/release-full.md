---
name: release-full
description: |
  Triggers: "release full", "release notes complete", "plan release end-to-end", "release ครบ"
  Orchestrates: plan-release → release-notes
model: sonnet
argument-hint: "[--name version]"
---

# /release-full

Orchestrates: `plan-release` → `release-notes`

## Steps

### Step 1 — Plan Release

Use the Skill tool to invoke `atlassian-pm:plan-release` with `$ARGUMENTS`.
Release context flows via conversation.

### Step 2 — Release Notes

> **Gate:** Confirm Step 1 produced a release plan (version name, included issues in conversation context). If plan-release failed or returned no issues, STOP.

Ask: "Generate and publish release notes now?"
→ If yes: Use the Skill tool to invoke `atlassian-pm:release-notes`
→ If no: exit after release plan
