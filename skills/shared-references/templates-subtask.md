# Sub-task & QA Templates (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, panel types, styling

## Subtask Best Practices

**SMART Criteria:**

| Criteria | Meaning | Red Flag |
| --- | --- | --- |
| **S**pecific | Clear what to do | "Do backend part" (vague) |
| **M**easurable | Can tell when done | No AC or definition of done |
| **A**chievable | One person can complete | Requires 3 people to coordinate |
| **R**elevant | Matches parent story | Unrelated to story scope |
| **T**ime-boxed | ≤ 1 day (4-8 hours) | Takes 3 days |

**Size Guide:**

| Size | Duration | Guideline |
| --- | --- | --- |
| XS | < 2 hours | May be too small — consider merging with another subtask |
| S | 2-4 hours | Appropriate |
| M | 4-8 hours (1 day) | Appropriate — upper bound |
| L | > 1 day | Must split — too large for a subtask |

**Ideal Count:** 3-10 subtasks per story (sweet spot: 5-7). < 3 → story may not need decomposition. > 10 → story too large, split with SPIDR first.

**Decomposition Techniques:**

| Technique | Method | Example |
| --- | --- | --- |
| By Layer | Split by service tag | [BE] API + [FE-Admin] UI + [QA] Test |
| By Step | Split by workflow stage | DB migration → API endpoint → UI form → Integration test |
| By Scenario | Split by parent AC | Happy path → Edge case → Error handling |
| By Component | Split by module | Form component → List component → Filter component |

**Rules:** Prefer vertical slice when possible | Each subtask independently completable by one person | Every subtask must have clear definition of done | Never create "leftover" or "miscellaneous" subtasks

**Anti-Patterns:** Over-layering (deep hierarchy = admin overhead) | No AC (can't tell when done) | Subtask replacing story split (hiding value in subtask) | Generic paths ("fix backend files") | Copy-paste AC from parent (subtask AC should be more specific)

**Jira Fields (set in Step 1 MCP create via `additional_fields`):**

| Field | Jira ID | Value | Required |
| --- | --- | --- | --- |
| Original Estimate | `timetracking` | `{"originalEstimate": "4h"}` (e.g. 1d, 4h, 30m) | Yes |
| Start Date | `{{START_DATE_FIELD}}` | `"YYYY-MM-DD"` (within parent date range — HR8) | Recommended |
| Due Date | `duedate` | `"YYYY-MM-DD"` (within parent date range — HR8) | Recommended |

> **Do NOT set sprint on subtasks** (HR10) — inherits from parent automatically.
>
> **Estimation:** Set BOTH the ADF `⏱️ Estimation` panel (human-readable) AND `timetracking` field (machine-queryable).
>
> **Example Step 1:** `jira_create_issue(project_key="{{PROJECT_KEY}}", summary="[BE] ...", issue_type="Subtask", additional_fields={"parent":{"key":"ABC-XXX"}, "timetracking":{"originalEstimate":"4h"}, "{{START_DATE_FIELD}}":"2026-02-10", "duedate":"2026-02-11"})`

## Sub-task Template (ADF) - TWO-STEP WORKFLOW

> **Content Budget** → see [writing-style.md](writing-style.md#content-budget-per-section)

**Density rules:**

- Objective: **1 sentence** — Thai narrative, English technical terms
- Scope table: `Action | File` single table, **max 10 rows** — CREATE/MODIFY/REF, ≥1 REF required
- AC: **max 3 panels** — all `panelType: "success"`, Given/When/Then with specific method names + HTTP codes
- Reference section: ⚡ **skip** if parent story has all links

> ⚠️ **CRITICAL:** `acli jira workitem create` does not support the `parent` field!
>
> **Must use Two-Step Workflow:**
>
> 1. **Step 1:** Create Sub-task shell with MCP (supports parent)
> 2. **Step 2:** Update description with acli + ADF

### Step 1: Create Sub-task Shell (MCP)

```typescript
jira_create_issue({
  project_key: "{{PROJECT_KEY}}",
  summary: "[TAG] - Description",
  issue_type: "Subtask",
  additional_fields: { parent: { key: "ABC-XXX" } }  // Parent Story key
})
```

### Step 2: Update Description (acli + ADF)

> Used with `acli jira workitem edit --from-json ... --yes`

**Scope table Action values:**

- `CREATE` — new file to create from scratch
- `MODIFY` — existing file to add/change code
- `REF` — existing file to read as pattern (developer follows the pattern, does NOT change the file)

```json
{
  "issues": ["ABC-YYY"],
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "1. Objective"}]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "[Thai sentence describing what and why — e.g., สร้าง LineNotificationChannel ที่ส่ง push message ผ่าน LINE Messaging API]"}
      ]},
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "2. Scope"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Action"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "File"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "CREATE"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "app/Services/Feature/NewService.ts", "marks": [{"type": "code"}]}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "MODIFY"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "app/Services/Existing/RegisterService.ts", "marks": [{"type": "code"}]}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "REF"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "app/Services/Similar/ExistingChannel.ts", "marks": [{"type": "code"}]},
              {"type": "text", "text": " (pattern reference)"}
            ]}]}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "3. Acceptance Criteria"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "success"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "AC1: [Verb] — [Scenario]", "marks": [{"type": "strong"}]}]},
          {"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[precondition — specific state, e.g., user มี LINE accounts ที่ is_enabled = true]"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "When: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[action — reference real method/endpoint, e.g., channel "},
              {"type": "text", "text": "notify()", "marks": [{"type": "code"}]},
              {"type": "text", "text": " ถูกเรียก]"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[result — specify HTTP status code, exact UI message, or observable behavior]"}
            ]}]}
          ]}
        ]
      }
    ]
  }
}
```

## QA Test Case Template (ADF) - TWO-STEP WORKFLOW

> ⚡ **Optional** — create only when requested by QA team or story has complex business logic requiring a clear test plan
>
> Same Two-Step as Sub-task above: MCP create (`summary: "[QA] - Test: [Feature Name]"`) → acli edit

**Density rules:**

- Test Objective: **1 sentence**
- Test Cases: **max 8 cases** — if >8, split QA ticket
- Each TC: **3 bullets** (Given/When/Then) + AC ref + Priority — no prose

> **Important:** Use bulletList inside panels (not nested tables)

```json
{
  "issues": ["ABC-YYY"],
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🎯 Test Objective"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "[What this test validates]"}]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📊 AC Coverage"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "#"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#f4f5f7"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Scenarios"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "1"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[AC1 desc]"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "TC1, TC2"}]}]}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🧪 Test Cases"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "success"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "TC1: [Happy Path Test]", "marks": [{"type": "strong"}]}]},
          {"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "AC: 1 | Priority: 🟠 High"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[precondition]"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "When: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[action]"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[expected result]"}
            ]}]}
          ]}
        ]
      },
      {
        "type": "panel",
        "attrs": {"panelType": "warning"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "TC2: [Edge Case Test]", "marks": [{"type": "strong"}]}]},
          {"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "AC: 2 | Priority: 🟡 Medium"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[edge condition]"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "When: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[action]"}
            ]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]},
              {"type": "text", "text": "[expected result]"}
            ]}]}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🔗 Reference"}]},
      {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
        "content": [
          {"type": "tableRow", "content": [
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Type"}]}]},
            {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Link"}]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "User Story"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "ABC-XXX", "marks": [{"type": "link", "attrs": {"href": "https://{{JIRA_SITE}}/browse/ABC-XXX"}}]}
            ]}]}
          ]}
        ]
      }
    ]
  }
}
```
