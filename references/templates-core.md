# ADF Core Rules & Patterns

## CREATE vs EDIT

> **CRITICAL:** Different JSON formats — never interchange!

| Operation | Required | Forbidden |
| --- | --- | --- |
| **CREATE** | `projectKey`, `type`, `summary`, `description` | `issues` |
| **EDIT** | `issues`, `description` | `projectKey`, `type`, `summary`, `parent` |

`unknown field "projectKey"` → CREATE format on EDIT · `unknown field "issues"` → EDIT format on CREATE

## Panel Types

| Type | Usage |
| --- | --- |
| `info` | Story narrative, objective, summary |
| `success` | Happy path AC |
| `warning` | Edge cases, validation |
| `error` | Error handling, negative tests |
| `note` | Notes, dependencies |

## Content Rules

| Section | Use | Never |
| --- | --- | --- |
| Acceptance Criteria | panels + Given/When/Then | table alone |
| Fields/Spec | table | panels |
| Notes/Dependencies | `note` panel | table |
| Table inside panel | bulletList | nested table/list |

AC panels: happy path → `success` · edge cases → `warning` · errors → `error`

AC Summary table (ID/Title/Type/Description columns) optional for stories with AC ≥ 5.

## Inline Code

Mark file paths, routes, functions: `{"type": "text", "text": "src/file.tsx", "marks": [{"type": "code"}]}`

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| `projectKey` in EDIT JSON | Use `issues` array only |
| `issues` in CREATE JSON | Use `projectKey`, `type`, `summary` |
| Missing `version: 1` | Always include in doc root |
| Wiki format | Use ADF JSON with acli |
| Nested bulletList | Flatten to single list |
| Missing marks array | `[{"type": "code"}]` not `"code"` |
