# Writing Style Guide

## Language Rules

### Thai + Transliteration

**Principle:** Main content in Thai, technical terms in English

| Content Type | Language | Example |
| --- | --- | --- |
| User Story narrative | Thai | "Admin wants to view coupon list" |
| AC descriptions | Thai | "When clicking the Submit button" |
| Technical terms | English | endpoint, payload, component |
| File paths | English | `src/pages/coupon/index.tsx` |
| Code/Routes | English | `/api/coupons`, `getCoupons()` |

**Keep as-is (no transliteration):** endpoint, payload, validate, component, service, API, route, model, schema, query, filter, response, request

### Correct Examples

**Good:**

```text
Given: Admin enters the `/coupon` page
When: Clicks "Top-up Credit Coupon"
Then: Navigates to `/coupon/topup-credit`
```

**Bad:**

```text
Given: Admin enters the coupon page  (❌ all English - no route reference)
When: Click "Top-up Credit Coupon"
Then: Navigate to topup credit page
```

## Tone & Style

> **3 Principles:** Concise (cut excess words) · Casual (talk like a teammate) · Clear (specific + testable)

| ❌ Verbose | ✅ Concise |
| --- | --- |
| The system shall render and display a total of 3 card types in accordance with the approved design specifications | Display 3 card types per design |
| Upon successful completion of page loading, the user shall be able to observe 3 card items rendered on screen | AC1: Display - Page loads and shows 3 cards |
| Then: Show an appropriate error | Then: Show error "Please enter an amount" |

## Scan-First Principle

Team will **scan before reading** — design content to be scannable in 5 seconds

1. **Bold keywords first** — `**Given:** precondition` not long prose
2. **Bullets > Paragraphs** — no long paragraphs, use bullet points
3. **Tables > Lists** — if 2+ columns of data, use table
4. **Skip if empty** — if a section has no real data, don't add placeholder
5. **Numbered sections** — prefix H2 headings with `N. Emoji Title` for easy reference

### Numbered Section Pattern

> **Preferred for Task/Epic with 4+ sections** — numbers let teammates reference "section 3" in standup

**Format:** `## N. 📋 Section Title` where N = sequential number, Emoji = section type

| Emoji | Section Type | When to use |
| --- | --- | --- |
| 📋 | Context / Overview | Always first — problem statement |
| 📊 | Data / Inventory | Tables, metrics, lists |
| 🔑 | Key Convention / Config | Standards, naming, settings |
| 🔧 | Phases / Steps | Implementation plan |
| ⚠️ | Scope / Boundaries | In-scope vs out-of-scope |
| ✅ | Acceptance Criteria | Done criteria, verification |
| 🔗 | Reference | Links, docs, related issues |

**ADF heading:**

```json
{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "1. 📋 Context"}]}
```

**Rules:**

- Numbers are sequential (1, 2, 3...) — no gaps
- Context/Overview always section 1, Reference always last
- Middle sections ordered by reading flow (data → plan → boundaries → criteria)
- Emoji is optional for simple tasks (<4 sections) but recommended for complex ones

## Storytelling Principles

> **Goal:** Every ticket must explain **why** before **what**

### Narrative Arc → Jira Mapping

| Framework | Jira Mapping |
| --- | --- |
| Three-Part (Jobs): Status Quo → Challenge → Solution | Epic: Problem line in Overview |
| Pixar Spine: Once upon a time → Every day | Story: 📍 Context line before "As a" |
| Scenario Naming | AC: `AC{N}: [Verb] — [Scenario]` |
| Event Causality: Command → Event → Policy | AC: Given=[state] When=[command] Then=[event effect] |

### Rules

1. **Problem before Solution** — Epic Overview starts with problem, not feature
2. **Context before Action** — Story opens with user's current situation (⚡ optional)
3. **Scenario Names > Numbers** — AC title describes _what happens_, not just "AC1"
4. **Business "Why" > Technical "What"** — "So that" must be business value, not technical benefit
5. **One Story per Ticket** — If narrative has 2 arcs → split ticket
6. **Event Causality** — ⚡ optional: specify related domain events (Command → Event → side effect) for traceability

### Anti-Patterns

| Pattern | Problem | Fix |
| --- | --- | --- |
| No Problem Statement | Epic reads as feature list | Add "Problem:" line |
| Generic Persona | "As a user" repeated in every story | Add 📍 context line + specific situation |
| Numbered-only ACs | "AC1", "AC2" are meaningless | Use verb + scenario name |
| Restated Why | "So that I can do X" = copy of "I want X" | "So that" must add new business value |
| Technical Events in AC | "DB_INSERT_SUCCESS" in AC | Use domain language: "CouponCollected" |
| No Event Flow | Story doesn't specify events | ⚡ optional: add command→event in AC title |

## Content Budget (per section)

> Agent **must** write within this budget — if exceeded, cut or split

| Issue Type | Section | Budget |
| --- | --- | --- |
| **Epic** | Overview | 3 lines (Problem + Summary + Supports) |
| | Business Value | 3 bullets (Revenue/Retention/Ops) |
| | Scope | 1 line/item, no description needed |
| | RICE | ⚡ optional — skip if priority is already clear |
| | Success Metrics | ⚡ optional — skip if metrics not yet defined |
| | User Stories | list + link only, no description |
| | Progress | auto counts, don't write manually |
| **Story** | Narrative | 3-4 lines (⚡ optional 📍 context + As a / I want / So that) |
| | AC panels | max 5 panels — if >5, split story |
| | Each AC | 3 bullets (Given/When/Then) + optional And |
| | Out of Scope | ⚡ optional — เพิ่มเมื่อมี adjacent feature ที่ developer อาจ assume ว่าต้องทำ |
| | Reference | ⚡ skip if no Figma/external link |
| **Task** | Context/Objective | 1-2 lines |
| | Out of Scope | ⚡ optional — เพิ่มเมื่อ task มี adjacent scope ที่อาจสับสน (refactor/spike) |
| **Sub-task** | Objective | 1 sentence |
| | Scope table | only files that change, max 10 rows |
| | AC panels | max 3 panels |
| | Reference | ⚡ skip if parent story has all links |
| **QA** ⚡ | Test Objective | 1 sentence |
| | Test Cases | max 8 cases — if >8, split QA ticket |

**⚡ = optional** — section or issue type included only when needed (QA ticket not required for every story)

## ADF Formatting

### Inline Code

Use inline code for:

- File paths: `src/pages/coupon/index.tsx`
- Routes: `/coupon/topup-credit`
- Component names: `CouponCard`
- Function names: `getCoupons()`
- Config keys: `COUPON_TYPES`

**ADF Mark:**

```json
{"type": "text", "text": "/coupon/topup-credit", "marks": [{"type": "code"}]}
```

### Bold Text

Use bold for:

- Labels: **Given**, **When**, **Then**
- Emphasis: **important**
- Section headers in content

**ADF Mark:**

```json
{"type": "text", "text": "Given:", "marks": [{"type": "strong"}]}
```

## Summary Format

### User Story

```text
[Service Tag] - [Description] ([English feature name])
```

Examples:

- ✅ `[FE-Admin] - Create coupon menu page (Coupon Menu)`
- ✅ `[BE] - Add API filter coupons`
- ❌ `Create coupon menu page` (no tag, English only)
- ❌ `[BE] - Build API` (not specific enough)

### Sub-task

```text
[TAG] - [Brief description]
```

Tags: `[BE]`, `[FE-Admin]`, `[FE-Web]`

### QA Sub-task

```text
[QA] - Test: [Story title or feature name]
```

## Common Mistakes

| Mistake | Correct |
| --- | --- |
| All English | Thai + transliteration |
| Too long | Concise, cut verbose words |
| Ambiguous | Specific, testable |
| Missing tag | Add `[BE]`, `[FE-Admin]`, etc. |
| Generic file paths | Actual paths from codebase |
