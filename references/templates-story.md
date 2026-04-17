# Story Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, styling.
> **Dual-Zone AC:** Read [templates-epic.md](templates-epic.md#dual-zone-acceptance-criteria-convention) for full convention.

## Story Overview

**Summary:** `[FE-Web/FE-Admin/BE/Video/AI-Agent] Story title — user-value outcome`
**Type:** Story (vertical slice or feature deliverable)

Both Business AC and Developer AC zones are **required** for Story.

## Dual-Zone Acceptance Criteria Convention

### Zone Definitions

**H3 "Acceptance Criteria — Business (มุมธุรกิจ/PM/ผู้ใช้)"**

- bulletList of observable user outcomes
- NO implementation detail — no service names (Pusher/S3/Redis), no SLA numbers, no patterns (async/fire-and-forget/debounce), no method names, no field names
- Outcomes only — what the user/PM observes

**H3 "Acceptance Criteria — Developer (มุม dev/QA/AI agent)"**

- bulletList of testable/executable specs
- MUST be concrete — SLA numbers, service names, patterns, test hooks all allowed
- Must reference Business AC IDs: `(derived from B-AC1, B-AC2)`
- Must have at least 1 bullet; Given/When/Then encouraged

### Per-Type Requirement (Story)

| Zone | Requirement |
| --- | --- |
| Business AC | required |
| Developer AC | required |

### Cross-Reference Rule

Developer AC items MUST cite the Business AC IDs they implement: `Dev-AC1: [spec] (derived from B-AC1)`.

### Worked Example (Story — AI Review Notification)

```markdown
## เงื่อนไขที่ต้องผ่าน (Acceptance Criteria)

### Acceptance Criteria — Business (มุมธุรกิจ/PM/ผู้ใช้)

- B-AC1: Billboard owner ได้รับแจ้งเตือนทันทีเมื่อ AI ต้องการความช่วยเหลือ
- B-AC2: เมื่อ owner กดยืนยัน ระบบแสดงสถานะ "รับทราบแล้ว" ทันที

### Acceptance Criteria — Developer (มุม dev/QA/AI agent)

- Dev-AC1: Notification delivered within 30s p95 via in-app channel; `notification_logs` row `status=sent` (derived from B-AC1)
- Dev-AC2: POST `/api/reviews/{id}/confirm` returns 200; `billboard_reviews.status` = `reviewed`; FE polling detects change within 2s (derived from B-AC2)
- Dev-AC3: regression — auto-approve path does NOT send review notification (paired: {{PROJECT_KEY}}-183)
```

## ADF Structure for Story

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Story",
  "summary": "[BE] Story title — user-value outcome",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "สิ่งที่ผู้ใช้ต้องการ"}]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "As a ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[specific persona — not 'user'],"}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "I want to ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[action],"}
      ]},
      {"type": "paragraph", "content": [
        {"type": "text", "text": "So that ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[business benefit — at least 10 chars]"}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "เงื่อนไขที่ต้องผ่าน (Acceptance Criteria)"}]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Acceptance Criteria — Business (มุมธุรกิจ/PM/ผู้ใช้)"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "B-AC1: [observable user outcome — no service names, no SLA numbers, no patterns]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "B-AC2: [observable user outcome]"}]}]}
      ]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Acceptance Criteria — Developer (มุม dev/QA/AI agent)"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dev-AC1: [concrete spec — SLA/service/GWT allowed] (derived from B-AC1)"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dev-AC2: [concrete spec] (derived from B-AC1, B-AC2)"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขอบเขต (Scope)"}]},
      {"type": "panel", "attrs": {"panelType": "note"}, "content": [
        {"type": "paragraph", "content": [
          {"type": "text", "text": "รวม: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[in-scope features]"}
        ]},
        {"type": "paragraph", "content": [
          {"type": "text", "text": "ไม่รวม: ", "marks": [{"type": "strong"}]},
          {"type": "text", "text": "[explicit out-of-scope]"}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "References"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Parent Epic: "},
          {"type": "inlineCard", "attrs": {"url": "https://{{JIRA_SITE}}/browse/TP-XXX"}}
        ]}]}
      ]}
    ]
  }
}
```

## Rules

- Both AC zones required for Story
- Business zone: no tech jargon (see banned token list in [templates-epic.md](templates-epic.md#dual-zone-acceptance-criteria-convention))
- Developer zone: Given/When/Then encouraged; must cite B-AC IDs
- ADF text purity: never embed markdown in text nodes (`\n\n`, `|...|`, `•`, `#`) — always use ADF structural blocks
- Validator `S8` checks both zones; `S7` checks for markdown-in-text
