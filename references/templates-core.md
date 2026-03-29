# ADF Core Rules & Patterns

## CREATE vs EDIT - Different JSON Formats

> **CRITICAL:** JSON for create and edit have different formats — never use them interchangeably!

| Operation | Required Fields | Forbidden Fields |
| --- | --- | --- |
| **CREATE** (new issue) | `projectKey`, `type`, `summary`, `description` | `issues` |
| **EDIT** (existing issue) | `issues`, `description` | `projectKey`, `type`, `summary`, `parent` |

### CREATE Example

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Story",
  "summary": "Feature title",
  "description": { "type": "doc", "version": 1, "content": [...] }
}
```

### EDIT Example

```json
{
  "issues": ["ABC-XXX"],
  "description": { "type": "doc", "version": 1, "content": [...] }
}
```

> **Error Prevention:**
>
> - If you see `Error: json: unknown field "projectKey"` → you are using CREATE format with the EDIT command
> - If you see `Error: json: unknown field "issues"` → you are using EDIT format with the CREATE command

## Panel Types & Colors

| Panel Type | Color | Usage |
| --- | --- | --- |
| `info` | 🔵 Blue | Story narrative, objective, summary |
| `success` | 🟢 Green | Happy path AC, completed items |
| `warning` | 🟡 Yellow | Edge cases, validation, UI tests |
| `error` | 🔴 Red | Error handling, negative tests |
| `note` | 🟣 Purple | Notes, dependencies, important info |

## Important Rules

| Section | Format | ❌ Never Use |
| --- | --- | --- |
| **Acceptance Criteria** | panels + Given/When/Then | table alone |
| **AC Summary** | table (optional) | - |
| **Fields/Spec** | table | panels |
| **Notes/Dependencies** | panel (note) | table |
| **H2 headings (4+ sections)** | `N. Emoji Title` numbered | unnumbered headings |

### AC Format: Hybrid Approach (Recommended)

**Primary:** panels + Given/When/Then (always required)
**Optional:** AC Summary table (for Stories with AC ≥ 5)

**AC Summary Table (ADF):**

```json
{"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "📋 AC Summary"}]},
{
  "type": "table",
  "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
  "content": [
    {"type": "tableRow", "content": [
      {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ID"}]}]},
      {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Title"}]}]},
      {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Type"}]}]},
      {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Description"}]}]}
    ]},
    {"type": "tableRow", "content": [
      {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC-01", "marks": [{"type": "strong"}]}]}]},
      {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Display Fields"}]}]},
      {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "✅ Happy"}]}]},
      {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "System displays relevant fields when type is selected"}]}]}
    ]}
  ]
},
{"type": "rule"},
{"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "📝 AC Details"}]}
```

> **Rule:** AC Details (panels) are always required - Summary table is optional
>
> Even if the original data (wiki markup) is a table, it must be converted to panels + Given/When/Then format
>
> - Happy path → `panelType: "success"`
> - Validation/Edge cases → `panelType: "warning"`
> - Error handling → `panelType: "error"`

## Table Styling

Use `"attrs": {"background": "HEX"}` on `tableHeader` or `tableCell`. Same color for entire header row — do not mix colors in same row.

**ADF Pattern:** `{"type": "tableHeader", "attrs": {"background": "HEX_CODE"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Column Name"}]}]}`

| Category | Hex Code | Usage |
| --- | --- | --- |
| Default / Header | `#f4f5f7` | Generic tables, header rows |
| New / Create | `#e3fcef` | Files to be created, happy path |
| Modify / Warning | `#fffae6` | Files to be modified, edge cases |
| Delete / Error | `#ffebe6` | Files to be deleted, errors |
| Reference / Notes | `#eae6ff` | Links, dependencies, notes |
| Requirements | `#deebff` | Specs, requirements |
| Info highlight | `#e6fcff` | Information highlight |

## Inline Code

Mark file paths, routes, components, functions with `{"type": "code"}`:

```json
{"type": "text", "text": "src/pages/coupon/index.tsx", "marks": [{"type": "code"}]}
```

Mixed text: wrap only the code portion in marks, leave surrounding text plain.

## Common Mistakes

| Mistake | Correct |
| --- | --- |
| Table inside panel | Use bulletList inside panel |
| Using `projectKey` in EDIT JSON | Remove - only use `issues` array |
| Using `issues` in CREATE JSON | Remove - use `projectKey`, `type`, `summary` |
| `Error: unknown field "projectKey"` | You're using CREATE format with EDIT command |
| Missing `version: 1` | Always include in doc root |
| Using wiki format | Use ADF JSON with acli |
| Nested tables | Flatten or use lists |
| Nested bulletList (listItem > bulletList) | Flatten to single list or use comma-separated text |
| Missing marks array | Use `[{"type": "code"}]` not `"code"` |
