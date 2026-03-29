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

**Density rules:**

- Narrative: **3-4 lines** (⚡ optional 📍 Context + As a / I want / So that) — context line only when persona needs grounding
- AC: **max 5 panels** — if >5, split story (SPIDR)
- Each AC: **3 bullets** (Given/When/Then) + optional And — no prose
- Reference: ⚡ **skip** if no Figma/external link

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Story",
  "summary": "[Feature Name] - Thai Description",
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
            {"type": "text", "text": "📍 ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[User's current situation — what they're doing, what's difficult] ⚡ optional"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "As a ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[persona]"},
            {"type": "text", "text": ","}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "I want to ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[action]"},
            {"type": "text", "text": ","}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "So that ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[benefit]"}
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
      },
      {
        "type": "panel",
        "attrs": {"panelType": "warning"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "⛔ Out of Scope: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[สิ่งที่ไม่ต้องทำในรอบนี้] (จะ implement ใน [TICKET-XXX])"}
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
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Epic"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "ABC-XXX", "marks": [{"type": "link", "attrs": {"href": "https://{{JIRA_SITE}}/browse/ABC-XXX"}}]}
            ]}]}
          ]},
          {"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Figma"}]}]},
            {"type": "tableCell", "content": [{"type": "paragraph", "content": [
              {"type": "text", "text": "Design", "marks": [{"type": "link", "attrs": {"href": "[Figma URL]"}}]}
            ]}]}
          ]}
        ]
      },
      {"type": "rule"},
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📐 Technical Notes"}]},
      {
        "type": "panel",
        "attrs": {"panelType": "note"},
        "content": [
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Architecture guardrails: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[patterns/conventions to follow — e.g. repo pattern, event-driven, auth middleware]"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Key files: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[relevant file paths from codebase exploration — populated after Phase 6]"}
          ]},
          {"type": "paragraph", "content": [
            {"type": "text", "text": "Previous learnings: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": "[anti-patterns or pitfalls from related past stories — leave blank if none known]"}
          ]}
        ]
      }
    ]
  }
}
```

> **⚡ Technical Notes section is optional** — include when `domain_context` is available (Phase 1 Confluence search) or after codebase exploration (Phase 6). Skip if no relevant context exists. Update via `acli jira workitem edit --from-json` after Phase 7 if richer technical notes become available post-exploration.

**AC Scenario Naming** (5-8 words max, read as mini-story):

| Panel | Pattern | Example |
| --- | --- | --- |
| success | `AC{N}: [Verb] — [Happy scenario]` | `AC1: Display — Admin sees 3 card types` |
| warning | `AC{N}: [Verb] — [Edge scenario]` | `AC2: Validate — Required field left empty` |
| error | `AC{N}: [Verb] — [Error scenario]` | `AC3: Handle — API return 500` |

⚡ **Event-based** (use when Epic has Domain Model): `AC{N}: [DomainEvent/Invariant/FailureEvent] — [Scenario]` — e.g. `AC1: CouponCollected — User successfully collects coupon`
