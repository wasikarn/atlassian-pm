# Subtask Template (ADF)

> **Prerequisite:** Read [templates-core.md](templates-core.md) for CREATE/EDIT rules, styling.
> **Dual-Zone AC:** Read [templates-epic.md](templates-epic.md#dual-zone-acceptance-criteria-convention) for full convention.

## Subtask Overview

**Summary:** `[BE/FE-Admin/FE-Web/QA/Video/AI-Agent] Subtask title`
**Type:** Subtask (child of Story or Task)

Subtasks **inherit** parent's Business AC zone — no need to repeat it. Only Developer AC zone is required.

## Dual-Zone Acceptance Criteria Convention

### Per-Type Requirement (Subtask)

| Zone | Requirement |
| --- | --- |
| Business AC | inherit parent (skip — do NOT repeat) |
| Developer AC | required |

### Zone Definition

**Developer AC (required)** — concrete, testable specs scoped to this subtask only.

- Given/When/Then format recommended
- May reference parent story's B-AC IDs when clarifying scope: `(contributes to B-AC2)`
- Must have at least 1 bullet

### Worked Example (Subtask — [BE] Notification Trigger)

```markdown
## Acceptance Criteria — Developer (มุม dev/QA/AI agent)

- Dev-AC1: Given `AiReviewJob` dispatches `ReviewRequestedEvent`, When `NotificationService.send()` is called, Then `notification_logs` row is created with `status=queued` within 100ms (contributes to parent B-AC1)
- Dev-AC2: Idempotency key `review_id + owner_id` prevents duplicate row on retry
- Dev-AC3: Unit test: `NotificationServiceTest::test_send_creates_log_row` passes
```

## ADF Structure for Subtask

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Subtask",
  "summary": "[BE] Subtask title",
  "parent": "{{PARENT_KEY}}",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Objective"}]},
      {"type": "paragraph", "content": [{"type": "text", "text": "[1-2 sentence objective — what this subtask implements]"}]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Scope"}]},
      {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Action"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "File"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "MODIFY"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "app/Services/NotificationService.ts", "marks": [{"type": "code"}]}
          ]}]}
        ]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Acceptance Criteria — Developer (มุม dev/QA/AI agent)"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dev-AC1: [concrete spec — Given/When/Then] (contributes to parent B-AC1)"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dev-AC2: [concrete spec]"}]}]}
      ]},

      {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "References"}]},
      {"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [
          {"type": "text", "text": "Parent: "},
          {"type": "inlineCard", "attrs": {"url": "https://{{JIRA_SITE}}/browse/TP-XXX"}}
        ]}]}
      ]}
    ]
  }
}
```

## Rules

- Business AC zone: SKIP (inherit parent) — do not repeat parent's business ACs
- Developer AC zone: REQUIRED — at least 1 bullet, scoped to this subtask
- Summary MUST start with service tag: `[BE]`, `[FE-Admin]`, `[FE-Web]`, `[QA]`, `[Video]`, `[AI-Agent]`
- ADF text purity: never embed markdown in text nodes — use ADF structural blocks only
- Validator `S8` skips business zone check for subtask; `S7` checks markdown-in-text
