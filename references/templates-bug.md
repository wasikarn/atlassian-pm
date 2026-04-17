# Bug Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, styling.
> **Dual-Zone AC:** Read [templates-epic.md](templates-epic.md#dual-zone-acceptance-criteria-convention) for full convention.

## Bug Overview

**Summary:** `[Bug] Title — affected area (severity: Critical/High/Medium/Low)`
**Type:** Bug (production defect or QA-reported failure)

Both Business AC (symptom + expected behavior) and Developer AC (repro + fix acceptance) zones are **required** for Bug.

## Dual-Zone Acceptance Criteria Convention

### Per-Type Requirement (Bug)

| Zone | Requirement |
| --- | --- |
| Business AC | required — symptom description + expected behavior |
| Developer AC | required — repro steps + fix acceptance criteria |

### Zone Definitions for Bug

**Business AC** — describes the problem from user perspective and what "fixed" looks like to them:

- B-AC1: [symptom — what the user observes as broken]
- B-AC2: [expected behavior — what should happen instead]
- NO implementation detail (no stack traces, no class names, no DB queries in this zone)

**Developer AC** — concrete fix acceptance and regression guards:

- Dev-AC1: [repro condition — Given/When/Then] (derived from B-AC1)
- Dev-AC2: [fix acceptance — specific DB state, HTTP status, UI state] (derived from B-AC2)
- Dev-AC3: [regression guard — existing passing path still works]

### Worked Example (Bug — Notification Not Delivered)

```markdown
## เงื่อนไขที่ต้องผ่าน (Acceptance Criteria)

### Acceptance Criteria — Business (มุมธุรกิจ/PM/ผู้ใช้)

- B-AC1: Billboard owner ไม่ได้รับแจ้งเตือนเมื่อ AI ส่งคำขอ review (พบใน production 2026-04-15)
- B-AC2: หลัง fix แล้ว owner ต้องได้รับแจ้งเตือนทุกครั้งที่มีคำขอ review ใหม่

### Acceptance Criteria — Developer (มุม dev/QA/AI agent)

- Dev-AC1: Given `billboard_reviews.status` transitions to `pending_review`, When `NotificationJob` runs, Then `notification_logs` row created with `status=sent` within 30s (derived from B-AC1, B-AC2)
- Dev-AC2: Regression: existing `auto-approve` path continues to set `status=approved` without creating `notification_logs` row (paired: {{PROJECT_KEY}}-183)
- Dev-AC3: Unit test `NotificationJobTest::test_sends_on_pending_review` passes
```

## ADF Structure for Bug

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Bug",
  "summary": "[Bug] Notification not delivered — billboard owner (severity: High)",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "รายละเอียดปัญหา"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[What is broken, who is affected, when it started, severity]"}]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "ขั้นตอนทำซ้ำ"}]},
      {"type": "orderedList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Step 1]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Step 2]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Step 3 — observe bug]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "คาดหวัง vs เกิดจริง"}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "คาดหวัง"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "เกิดจริง"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[expected behavior]"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[actual behavior]"}]}]}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "เงื่อนไขที่ต้องผ่าน (Acceptance Criteria)"}]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Acceptance Criteria — Business (มุมธุรกิจ/PM/ผู้ใช้)"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "B-AC1: [symptom — what user observes as broken, no tech detail]"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "B-AC2: [expected behavior after fix — observable by user/PM]"}]}]}
      ]},
      {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Acceptance Criteria — Developer (มุม dev/QA/AI agent)"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dev-AC1: [repro + fix acceptance — Given/When/Then, specific DB/HTTP/UI state] (derived from B-AC1)"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dev-AC2: regression — [related path] still works correctly (derived from B-AC2)"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "References"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Related Epic: "},
          {"type": "inlineCard", "attrs": {"url": "https://{{JIRA_SITE}}/browse/TP-XXX"}}
        ]}]}
      ]}
    ]
  }
}
```

## Rules

- Both AC zones required for Bug
- Business zone: symptom + expected behavior; no stack traces, no class names
- Developer zone: repro steps + fix acceptance + at least 1 regression guard
- ADF text purity: never embed markdown in text nodes — use ADF structural blocks only
- Validator `S8` checks both zones; `S7` checks markdown-in-text
