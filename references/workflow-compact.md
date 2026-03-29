# Workflow Patterns (Compact)

> Extract from workflow-patterns.md — gate definitions and QG scoring only.

## Gate Levels

| Level | Symbol | Behavior |
| --- | --- | --- |
| **AUTO** | 🟢 | Validate automatically. Pass → proceed. Fail → auto-fix (max 2). Still fail → escalate to user. |
| **REVIEW** | 🟡 | Present results to user, wait for quick confirmation. Default: proceed unless user objects. |
| **GATE** | ⛔ | STOP. Wait for explicit user approval before proceeding. |
| **ITERATE** | 🔄 | Present structured plan → ask user to annotate/approve → if annotated: revise + re-present (max 3 rounds) → if approved: proceed. |

## Quality Gate (QG) Scoring

> HR1: NEVER create/edit issues on Jira/Confluence before QG ≥ 90%.

1. Score each check with confidence (0-100%). Only report issues with confidence ≥ 80%.
2. Report: `Technical X/5 | [Domain] Quality X/N | Overall X%`
3. If < 90% → auto-fix → re-score (max 2 attempts)
4. If ≥ 90% → proceed to next phase automatically
5. If still < 90% after 2 fixes → escalate to user
6. Low-confidence items (< 80%) → flag as "needs review" but don't fail QG

### Report Format by Type

| Skill Type | Report Format |
| --- | --- |
| Epic | `Technical X/5 \| Epic Quality X/4 \| Overall X%` |
| Story | `Technical X/5 \| Story Quality X/6 \| Overall X%` |
| Subtask | `Technical X/5 \| Subtask Quality X/5 \| Overall X%` |
| Task | `Technical X/5 \| Quality X/6 \| Overall X%` |
| QA | `Technical X/5 \| QA Quality X/5 \| Overall X%` |
