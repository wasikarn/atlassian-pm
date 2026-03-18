# Story Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, panel types, styling

## Story Best Practices

**Size Guide:**

| Size | Duration | Hours | Guideline |
| --- | --- | --- | --- |
| XS | < 0.5 day | < 4h | Quick fix, config change, hotfix |
| S | 0.5-1 day | 4-8h | Simple feature, minor change |
| M | 1-2 days | 8-16h | Standard feature — Ideal |
| L | 2-4 days | 16-32h | Complex feature — consider splitting |
| XL | > 4 days | > 32h | Must split — use SPIDR |

**SPIDR Splitting (Mike Cohn):**

| Technique | Method | Example |
| --- | --- | --- |
| **S**pike | Research before split | "Spike: try Redlock for 2 days" |
| **P**ath | Split by user path | Card payment vs Apple Pay |
| **I**nterface | Split by device/platform | iOS vs Android vs Web |
| **D**ata | Split by data type | Credit vs discount vs cashback |
| **R**ules | Split by business rules | Coupon expired vs fully used vs cancelled |

Additional: Workflow Steps | CRUD | User Roles | Complexity (manual vs automated) | I/O Methods (manual vs file upload vs API)

**Narrative Anti-Patterns:**

| Pattern | Problem | Fix |
| --- | --- | --- |
| Generic Persona | "As a user" — no context | Specify role + situation |
| Solution Masking | "I want a modal" — UI solution, not goal | Write goal first, solution goes in AC |
| Missing Why | No "So that" or restates goal | Ask "so what?" until value is clear |
| Kitchen Sink | 1 story = 3 goals | Split with SPIDR |
| Tech Story | "As a developer, I want to refactor..." | Use Task instead of Story (no direct user value) |
| Copy-Paste | All stories look the same | Each story must have unique context |

**AC Best Practices:** No vague ACs ("loads fast" → "loads within 2 seconds") | Each AC independently testable | Cover happy + edge + error | Don't duplicate story narrative in AC | Write AC before sprint planning

**Jira Fields (set after create via MCP `jira_update_issue`):**

| Field | Jira ID | Value | Required |
| --- | --- | --- | --- |
| Story Points | `customfield_10016` | XS=1, S=2, M=3, L=5, XL=8 | Yes |
| Size | `customfield_10107` | `{"value": "M"}` | Yes |
| Start Date | `{{START_DATE_FIELD}}` | `"YYYY-MM-DD"` (sprint start or planned start) | Recommended |
| Due Date | `duedate` | `"YYYY-MM-DD"` (planned completion) | Recommended |

> **Size → Story Points mapping:** Use Size Guide above. Set both fields — Size for visual, Story Points for velocity tracking.
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
      }
    ]
  }
}
```

**AC Scenario Naming:**

| Panel Type | Pattern | Example |
| --- | --- | --- |
| success (happy) | `AC{N}: [Verb] — [Happy scenario]` | `AC1: Display — Admin sees 3 card types` |
| warning (edge) | `AC{N}: [Verb] — [Edge scenario]` | `AC2: Validate — Required field left empty` |
| error (error) | `AC{N}: [Verb] — [Error scenario]` | `AC3: Handle — API return 500` |

⚡ **Event-based AC naming** (optional — use for domain-rich features):

| Panel Type | Pattern | Example |
| --- | --- | --- |
| success | `AC{N}: [DomainEvent] — [Scenario]` | `AC1: CouponCollected — User successfully collects coupon` |
| warning | `AC{N}: [Invariant] — [Scenario]` | `AC2: DuplicateBlocked — User collects duplicate` |
| error | `AC{N}: [FailureEvent] — [Scenario]` | `AC3: CollectionFailed — Campaign expired` |

> Event-based naming is best when Epic has a Domain Model section — allows AC to trace back to event catalog

Scenario name: **5-8 words max**, read as mini-story — See [Storytelling Principles](writing-style.md#storytelling-principles)
