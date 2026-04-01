# Task Templates (ADF) — Unified

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules and styling.

All task types use Jira `"type": "Task"`. Mode is conveyed via summary prefix and content structure — not issue type.

**Jira Fields (set after create via MCP `jira_update_issue`):**

| Field | Jira ID | Value | Required |
| --- | --- | --- | --- |
| Story Points | `customfield_10016` | 1–8 based on effort | Recommended |
| Size | `customfield_10107` | `{"value": "S"}` | Recommended |
| Original Estimate | `timetracking` | `{"originalEstimate": "4h"}` | Recommended |
| Start Date | `{{START_DATE_FIELD}}` | `"YYYY-MM-DD"` | Optional |
| Due Date | `duedate` | `"YYYY-MM-DD"` | Optional |

**EDIT format:** Replace `"projectKey"` with `"issues": ["KEY"]` — all other fields identical.

---

## Mode: feature (default) — replaces Story + Subtask

**Use case:** Any deliverable work — feature, sub-task, or implementation unit.
**Summary:** `[BE/FE-Admin/FE-Web] Task title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| สิ่งที่ผู้ใช้ต้องการ | Yes | As a / I want / So that, or plain narrative |
| เงื่อนไขที่ต้องผ่าน | Yes | Given/When/Then with ✅/⚠️/❌ prefix per AC |
| ขอบเขตไฟล์ | Optional (AI) | Table: Action \| File path |
| คำแนะนำการพัฒนา | Optional (AI/vibe) | Table: Field \| Value |

**AC naming:** `AC{N}: [Verb] — [Scenario Name]`
**AC prefix:** ✅ happy path · ⚠️ edge case · ❌ error case

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Task",
  "summary": "[BE] Task title",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "สิ่งที่ผู้ใช้ต้องการ"}]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "As a ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[persona],"}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "I want to ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[action],"}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "So that ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[benefit]"}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "เงื่อนไขที่ต้องผ่าน"}]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "✅ AC1: Return data — Happy path", "marks": [{"type": "strong"}]}
      ]},
      {"type": "bulletList", "content": [
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
          {"type": "text", "text": "[result]"}
        ]}]}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "⚠️ AC2: Handle empty — Edge case", "marks": [{"type": "strong"}]}
      ]},
      {"type": "bulletList", "content": [
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
          {"type": "text", "text": "[result]"}
        ]}]}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "❌ AC3: Reject invalid — Error case", "marks": [{"type": "strong"}]}
      ]},
      {"type": "bulletList", "content": [
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
          {"type": "text", "text": "[result]"}
        ]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขอบเขตไฟล์"}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Action"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "File"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "CREATE"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "app/Services/NewService.ts", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "MODIFY"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "app/Models/User.ts", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "REF"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "app/Services/ExistingService.ts", "marks": [{"type": "code"}]}
          ]}]}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "คำแนะนำการพัฒนา"}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Field"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Value"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Entry Point"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "[primary file path]", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Pattern"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "[reference file to follow]", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Test Command"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "[test command]", "marks": [{"type": "code"}]}
          ]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dependencies"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[key imports]"}]}]}
        ]}
      ]}
    ]
  }
}
```

---

## Mode: qa — replaces create-testplan

**Use case:** QA test plan linked to a story.
**Summary:** `[QA] Story title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| วัตถุประสงค์ทดสอบ | Yes | 1 sentence — what is being tested and why |
| ชุดทดสอบ | Yes | TC1–TC8, each with Given/When/Then + Priority label |
| อ้างอิง | Optional | Story key, test environment URL |

**Abbreviated ADF structure:**

```
heading(2): วัตถุประสงค์ทดสอบ
paragraph: [1-sentence test objective]

heading(2): ชุดทดสอบ
paragraph(strong): TC1: [Verb] — [Scenario] · Priority: High
bulletList:
  listItem → paragraph: Given(strong) + [precondition]
  listItem → paragraph: When(strong) + [action]
  listItem → paragraph: Then(strong) + [expected result]
paragraph(strong): TC2: [Verb] — [Scenario] · Priority: Medium
bulletList: ...

heading(2): อ้างอิง
bulletList:
  listItem → paragraph: Story: {{PROJECT_KEY}}-XXX
  listItem → paragraph: Test env: [URL]
```

---

## Mode: bug — replaces bug-triage

**Use case:** Bug report from QA or production.
**Summary:** `[Bug] Title — affected area`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| รายละเอียดปัญหา | Yes | What is broken, who is affected, severity |
| ขั้นตอนทำซ้ำ | Yes | Numbered steps to reproduce |
| คาดหวัง vs เกิดจริง | Yes | Table: Expected \| Actual |
| เงื่อนไขที่ต้องผ่าน | Yes | Fix criteria — what must be true after fix |

**Abbreviated ADF structure:**

```
heading(2): รายละเอียดปัญหา
paragraph: [description of what is broken + who is affected]

heading(2): ขั้นตอนทำซ้ำ
orderedList:
  listItem → paragraph: [step 1]
  listItem → paragraph: [step 2]
  listItem → paragraph: [step 3]

heading(2): คาดหวัง vs เกิดจริง
table(layout:default):
  tableRow: tableHeader[คาดหวัง] | tableHeader[เกิดจริง]
  tableRow: tableCell[expected behavior] | tableCell[actual behavior]

heading(2): เงื่อนไขที่ต้องผ่าน
bulletList:
  listItem → paragraph: ✅ AC1: [fix criterion — happy path]
  listItem → paragraph: ❌ AC2: [regression guard — error case]
```

---

## Mode: spike

**Use case:** Research, investigation, proof of concept.
**Summary:** `[Spike] Title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| คำถามวิจัย | Yes | Main research question — 1 sentence |
| บริบท | Yes | Why this spike is needed, what decision it unblocks |
| พื้นที่สำรวจ | Yes | Bullet list of areas/topics to investigate |
| ผลการค้นหา | Optional | Populate only after spike is done — omit if no data yet |
| ข้อเสนอแนะ | Optional | Recommendations — populate only after spike is done |

**Abbreviated ADF structure:**

```
heading(2): คำถามวิจัย
paragraph: [main research question]

heading(2): บริบท
paragraph: [background — why this spike, what decision it informs]

heading(2): พื้นที่สำรวจ
bulletList:
  listItem → paragraph: [area 1]
  listItem → paragraph: [area 2]
  listItem → paragraph: [area 3]

heading(2): ผลการค้นหา          ← add after research, omit at creation
paragraph: [findings]

heading(2): ข้อเสนอแนะ           ← add after research, omit at creation
bulletList:
  listItem → paragraph: [recommendation]
```

---

## Mode: chore

**Use case:** Maintenance, dependency updates, configuration changes, CI/CD tasks.
**Summary:** `[Chore] Title`

**Sections:**

| Section | Required | Notes |
| --- | --- | --- |
| วัตถุประสงค์ | Yes | 1 sentence — what this chore achieves |
| รายการงาน | Yes | Bullet checklist with ⬜ prefix |
| เงื่อนไขที่ต้องผ่าน | Yes | Definition of done — what must be true when complete |

**Abbreviated ADF structure:**

```
heading(2): วัตถุประสงค์
paragraph: [1-sentence objective]

heading(2): รายการงาน
bulletList:
  listItem → paragraph: ⬜ [task item 1]
  listItem → paragraph: ⬜ [task item 2]
  listItem → paragraph: ⬜ [task item 3]

heading(2): เงื่อนไขที่ต้องผ่าน
bulletList:
  listItem → paragraph: ✅ [done criterion 1]
  listItem → paragraph: ✅ [done criterion 2]
```
