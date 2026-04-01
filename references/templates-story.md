# Story Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, panel types, styling

## Story Best Practices

> Split via SPIDR (Spike/Path/Interface/Data/Rules) if >5 ACs or >4 days effort. Also: Workflow Steps | CRUD | User Roles | I/O Methods.

**Jira Fields (set after create via MCP `jira_update_issue`):**

| Field | Jira ID | Value | Required |
| --- | --- | --- | --- |
| Story Points | `customfield_10016` | XS=1, S=2, M=3, L=5, XL=8 | Yes |
| Size | `customfield_10107` | `{"value": "M"}` | Yes |
| Start Date | `{{START_DATE_FIELD}}` | `"YYYY-MM-DD"` (sprint start or planned start) | Recommended |
| Due Date | `duedate` | `"YYYY-MM-DD"` (planned completion) | Recommended |

> **Size → Story Points mapping:** XS=1, S=2, M=3, L=5, XL=8. Set both fields — Size for visual, Story Points for velocity tracking.
>
> **Example:** `jira_update_issue(issue_key="ABC-XXX", additional_fields={"customfield_10016": 3, "customfield_10107": {"value": "M"}, "{{START_DATE_FIELD}}": "2026-02-10", "duedate": "2026-02-14"})`

## User Story Template (ADF) - CREATE

> Used with `acli jira workitem create --from-json`
>
> **Content Budget** → see [writing-style.md](writing-style.md#content-budget-per-section)

**Required sections (always include):**

- User Story narrative (📍 Context optional + As a / I want / So that)
- Acceptance Criteria (1–5 panels, Given/When/Then — no prose)

**Optional sections (⚡ include only when there is real data):**

- `⛔ Out of Scope` — เพิ่มเฉพาะเมื่อมี adjacent feature ที่ developer อาจ assume ว่าต้องทำ
- `🔗 Reference` — เพิ่มเฉพาะเมื่อมี Figma URL หรือ external link จริง ๆ (ไม่ใส่ placeholder)
- `📐 Technical Notes` — เพิ่มเฉพาะเมื่อ codebase exploration ส่งกลับ concrete file paths/patterns

> **Narrative tone:** Story narrative ต้องเขียนให้คนทั่วไปอ่านเข้าใจ — เขียนเป็นประสบการณ์ของผู้ใช้ ไม่ใช่ implementation detail
>
> - ❌ "As a user, I want to invoke the OAuth2 token refresh endpoint"
> - ✅ "As a member, I want to stay logged in without having to sign in again every day"
> - ❌ "So that the session persistence layer processes the JWT correctly"
> - ✅ "So that ฉันใช้แอปต่อได้ทันทีโดยไม่สะดุด"

**Default ADF (required sections only):**

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Story",
  "summary": "[Service Tag] - [Thai description]",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "User Story"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": [
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
            {"type": "text", "text": "[benefit — business value in plain language]"}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Acceptance Criteria"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "success"},
        "content": [
          {"type": "paragraph", "content": [{"type": "text", "text": "AC1: [Verb] — [Scenario Name]", "marks": [{"type": "strong"}]}]},
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
          ]}
        ]
      }
    ]
  }
}
```

**⚡ Optional snippets — append only when real data exists:**

```json
// 📍 Context line — prepend inside User Story panel when persona needs grounding
{"type": "paragraph", "content": [
  {"type": "text", "text": "📍 ", "marks": [{"type": "strong"}]},
  {"type": "text", "text": "[User's current situation — what's painful today]"}
]},

// ⛔ Out of Scope — append after last AC panel when adjacent scope needs clarifying
{"type": "rule"},
{"type": "panel", "attrs": {"panelType": "warning"}, "content": [
  {"type": "paragraph", "content": [
    {"type": "text", "text": "⛔ Out of Scope: ", "marks": [{"type": "strong"}]},
    {"type": "text", "text": "[สิ่งที่ไม่ต้องทำในรอบนี้] (จะ implement ใน [TICKET-XXX])"}
  ]}
]},

// 🔗 Reference — add only when Figma URL or external design link actually exists
{"type": "rule"},
{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🔗 Reference"}]},
{"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
  {"type": "tableRow", "content": [
    {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Type"}]}]},
    {"type": "tableHeader", "attrs": {"background": "#eae6ff"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Link"}]}]}
  ]},
  {"type": "tableRow", "content": [
    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Figma"}]}]},
    {"type": "tableCell", "content": [{"type": "paragraph", "content": [
      {"type": "text", "text": "Design", "marks": [{"type": "link", "attrs": {"href": "[Figma URL]"}}]}
    ]}]}
  ]}
]},

// 📐 Technical Notes — add ONLY after codebase exploration returns concrete data (Phase 7)
// Include only fields that have real values — skip any field with no data
{"type": "rule"},
{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📐 Technical Notes"}]},
{"type": "panel", "attrs": {"panelType": "note"}, "content": [
  {"type": "paragraph", "content": [
    {"type": "text", "text": "Key files: ", "marks": [{"type": "strong"}]},
    {"type": "text", "text": "[actual file paths from Phase 7 exploration]"}
  ]}
]}
```

**AC Scenario Naming** (5-8 words max, read as mini-story):

| Panel | Pattern | Example |
| --- | --- | --- |
| success | `AC{N}: [Verb] — [Happy scenario]` | `AC1: Display — Admin sees 3 card types` |
| warning | `AC{N}: [Verb] — [Edge scenario]` | `AC2: Validate — Required field left empty` |
| error | `AC{N}: [Verb] — [Error scenario]` | `AC3: Handle — API return 500` |

⚡ **Event-based** (use when Epic has Domain Model): `AC{N}: [DomainEvent/Invariant/FailureEvent] — [Scenario]` — e.g. `AC1: CouponCollected — User successfully collects coupon`
