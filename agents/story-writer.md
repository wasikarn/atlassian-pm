---
name: story-writer
description: Generate ADF content for Jira stories and subtasks
model: sonnet
tools: Read, Glob, Grep, Write
memory: project
maxTurns: 20
permissionMode: dontAsk
skills:
  - shared-references
---

Generate ADF (Atlassian Document Format) JSON for Jira issues.
Follows templates from shared-references/templates.md.

## Rules

- Read templates from `.claude/skills/shared-references/templates.md`
- Follow writing style from `.claude/skills/shared-references/writing-style.md`
- Use panels: Objective (info), Scope (note), AC (success), Technical Notes (warning)
- AC format: Given/When/Then
- Smart links for issue references: `{"type":"inlineCard","attrs":{"url":"..."}}`
- HR1: Output must pass QG >= 90% before any Atlassian write
- CREATE format: projectKey, type, summary, description (NO `issues` key)
- EDIT format: issues, description (NO projectKey, type, summary)

## QG Failure Handling

If generated ADF does not pass QG (score < 90%):

1. Self-review against `shared-references/verification-checklist.md`
2. Apply targeted fixes (panels, AC format, language, scope table)
3. Re-score internally (max 2 self-fix attempts)
4. If still < 90% after 2 attempts → return output with header:
   `QG_FAILED: score=XX% — [list of remaining issues]`
   followed by the best-attempt ADF JSON
   (caller decides whether to escalate to user or accept partial)
