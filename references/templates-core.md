# ADF Core Rules

## Issue Hierarchy

Epic → Task (2 levels only, no Story/Subtask)

## ADF Principles

1. No panel nodes — use heading + paragraph + bulletList + table only
2. No blockquote — never use `>` markdown syntax or ADF blockquote node
3. No emoji in headings — plain Thai text only
4. No horizontal rules between sections — headings create separation naturally
5. No numbered section headings — no "1. Context", "2. Scope" style prefixes
6. AC type prefix: ✅ (happy path) / ⚠️ (edge case) / ❌ (error/negative) in bold paragraph text (NOT in heading)

## Allowed ADF Node Types

| Node | Usage |
| --- | --- |
| `heading` (h2) | Section titles |
| `paragraph` | Content text |
| `bulletList` / `listItem` | Unordered lists |
| `orderedList` / `listItem` | Numbered steps |
| `table` / `tableRow` / `tableHeader` / `tableCell` | Structured data |
| `text` (marks: `strong`, `em`, `code`, `link`) | Inline formatting |

## Forbidden ADF Node Types

| Node | Why |
| --- | --- |
| `panel` | Renders as blockquote on some clients; use heading + content instead |
| `blockquote` | No visual hierarchy |
| `rule` | Headings create separation naturally |

## CREATE vs EDIT

> **CRITICAL:** Different JSON formats — never interchange!

| Operation | Required | Forbidden |
| --- | --- | --- |
| **CREATE** | `projectKey`, `type`, `summary`, `description` | `issues` |
| **EDIT** | `issues`, `description` | `projectKey`, `type`, `summary`, `parent` |

`unknown field "projectKey"` → CREATE format used on EDIT · `unknown field "issues"` → EDIT format used on CREATE

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
| Panel node in ADF | Replace with heading + paragraph/bulletList |
| Emoji in heading text | Move emoji to paragraph bold text only |
