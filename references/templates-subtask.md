# Sub-task & QA Templates (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, panel types, styling

## Subtask Fields

| Field | Jira ID | Value | Required |
| --- | --- | --- | --- |
| Original Estimate | `timetracking` | `{"originalEstimate": "4h"}` (1d/4h/30m) | Yes |
| Start Date | `{{START_DATE_FIELD}}` | `"YYYY-MM-DD"` (within parent range — HR8) | Recommended |
| Due Date | `duedate` | `"YYYY-MM-DD"` (within parent range — HR8) | Recommended |

> **HR10:** Do NOT set sprint on subtasks — inherits from parent.
> **Estimation:** Set BOTH ADF `⏱️ Estimation` panel (human-readable) AND `timetracking` field (machine-queryable).

**Step 1 example:**

```text
jira_create_issue(project_key="{{PROJECT_KEY}}", summary="[BE] ...", issue_type="Subtask",
  additional_fields={"parent":{"key":"ABC-XXX"}, "timetracking":{"originalEstimate":"4h"},
  "{{START_DATE_FIELD}}":"2026-02-10", "duedate":"2026-02-11"})
```

## Sub-task Template — TWO-STEP WORKFLOW

### Step 1: MCP Create Shell

```typescript
jira_create_issue({ project_key: "{{PROJECT_KEY}}", summary: "[TAG] - Description",
  issue_type: "Subtask", additional_fields: { parent: { key: "ABC-XXX" } } })
```

### Step 2: acli + ADF Description

> `acli jira workitem edit --from-json ... --yes`
> → see [templates-core.md](templates-core.md) for ADF doc/panel/table node format

**Density rules:**

- Objective: **1 sentence** — Thai narrative, English technical terms
- Scope table: `Action | File`, **max 10 rows** — ≥1 REF required
- AC: **max 3 panels** — all `panelType: "success"`, Given/When/Then with method names + HTTP codes
- Reference section: skip if parent story has all links

**Sections:** `1. Objective` → `2. Scope` → `3. Acceptance Criteria` → `4. 🤖 Implementation Hints`

**Scope table Action values:**

| Value | Meaning |
| --- | --- |
| `CREATE` | New file to create from scratch |
| `MODIFY` | Existing file to add/change code |
| `REF` | Existing file to read as pattern only — developer does NOT change it |

**AC panels:** all `panelType: "success"` · heading `AC1: [Verb] — [Scenario]` bold · bullets: Given/When/Then

### Section 4: Implementation Hints

> **Optional** — generate only when `--vibe` flag used OR codebase exploration data available.

**Why this matters:** The subtask IS the AI prompt — when a developer runs `implement {{PROJECT_KEY}}-123`, Claude reads this ticket via MCP. Good hints = production-ready first pass. No hints = generic code.

**Hint table (inside `panelType: "note"`):**

| Row | Required |
| --- | --- |
| Entry Point | Yes — primary file to CREATE or MODIFY |
| Pattern to Follow | Yes — REF file from Scope table |
| Test Command | Yes — exact command (e.g. `node ace test --files "tests/unit/services/feature*"`) |
| Related API | Optional — BE subtasks with HTTP endpoints only |
| Dependencies | Optional — injected services/repos the new file needs |

After the table, add a `Claude Code Prompt:` paragraph:

```text
Implement [objective] following the pattern in [Pattern to Follow]. Run [Test Command] to verify. All ACs must pass.
```

**Minimal ADF skeleton for Step 2:**

```json
{
  "issues": ["ABC-YYY"],
  "description": {
    "type": "doc", "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "1. Objective"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[Thai objective sentence]"}]},
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "2. Scope"}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Action"}]}]},
          {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "File"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "CREATE"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "app/Services/Feature/NewService.ts", "marks": [{"type": "code"}]}]}]}
        ]}
      ]},
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "3. Acceptance Criteria"}]},
      {"type": "panel", "attrs": {"panelType": "success"}, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "AC1: [Verb] — [Scenario]", "marks": [{"type": "strong"}]}]},
        {"type": "bulletList", "content": [
          {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[precondition]"}]}]},
          {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "When: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[action — real method/endpoint]"}]}]},
          {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]}, {"type": "text", "text": "[result — HTTP status or observable behavior]"}]}]}
        ]}
      ]}
    ]
  }
}
```

## QA Test Case Template

> Optional — create when QA requests or story has complex business logic.
> Summary format: `[QA] - Test: [Feature Name]` · Same Two-Step: MCP create → acli edit

**Density rules:**

- Test Objective: **1 sentence**
- Test Cases: **max 8 cases** — split QA ticket if >8
- Each TC: 3 bullets (Given/When/Then) + AC ref + Priority — no prose
- Use `bulletList` inside panels (not nested tables)

**Panel type by TC type:** happy path → `success` · edge case → `warning`

**Sections:** `🎯 Test Objective` (info panel) → `📊 AC Coverage` (table: # | AC | Scenarios) → `🧪 Test Cases` (panels) → `🔗 Reference` (table: Type | Link)

**AC Coverage table columns:** `#` | `AC` | `Scenarios`
**Reference table columns:** `Type` | `Link` (with hyperlink mark on issue key)

**Test Case panel structure:**

```text
TC1: [Happy Path Test]  ← bold paragraph
• AC: 1 | Priority: 🟠 High
• Given: [precondition]
• When: [action]
• Then: [expected result]
```

**Priority scale:** 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low
