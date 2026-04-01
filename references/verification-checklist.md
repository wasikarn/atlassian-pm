# Verification Checklist

> Standard checklists for verifying Jira issues

---

## Technical Checks (All Issue Types)

| Check | Criteria |
| --- | --- |
| **T1: ADF Format** | type: "doc"; version: 1; content array exists; no malformed nodes |
| **T2: Heading Structure** | Valid h2 headings for sections; no panel nodes; no blockquote nodes; no emoji in headings |
| **T3: Inline Code Marks** | file paths marked (e.g., `app/Models/User.ts`); API routes marked (e.g., `/api/v1/credits`); component names marked; technical terms marked appropriately |
| **T4: Links** | parent link exists (tasks with parent epic); epic link exists where applicable; child count matches (parents); external links valid |
| **T5: Required Fields** | summary filled; description not empty; issue type correct; project key correct ({{PROJECT_KEY}}); assignee/reporter set (if required) |

---

## Task Quality Checks

| Check | Criteria |
| --- | --- |
| **TK1: Objective** | Clear 1-2 sentence objective or user need; answers "what" and "why"; specific to this task |
| **TK2: Acceptance Criteria** | All ACs have Given/When/Then clauses; ACs are specific and measurable; cover happy path; cover error cases; ACs are independent; references real method names or endpoints where applicable |
| **TK3: Scope & Files** | File paths are real (not generic — Glob-validated); scope table uses Action\|File format when ≥2 files; config/enum MODIFY included if new value added |
| **TK4: QA Task** | Test objective clear; test cases cover AC happy path + edge + error; preconditions stated; steps specific; expected results defined |
| **TK5: Bug Task** | รายละเอียดปัญหา stated; ขั้นตอนทำซ้ำ listed; คาดหวัง vs เกิดจริง defined; ACs specify fix verification |
| **TK6: Tag & Summary** | Tag matches service: [BE], [FE-Admin], [FE-Web], [QA]; summary is descriptive; summary starts with tag |
| **TK7: Language** | Thai + transliteration consistent; technical terms in English; code/paths in English; no machine translation artifacts |

---

## Vertical Slice Quality Checks

| Check | Criteria |
| --- | --- |
| **VS1: Slice Integrity** | Story delivers end-to-end user value; all required layers touched (UI → API → DB or subset); story is independently deployable; story is testable without other slices |
| **VS2: Labeling (MANDATORY)** | Has feature label (e.g., coupon-web, credit-topup); has VS label (e.g., vs1-skeleton, vs2-credit-e2e, vs-enabler); label matches pattern: `vs{N}-{name}` for numbered, `vs-enabler` for shared, `{feature}-{scope}` for cross-cutting |
| **VS3: Anti-patterns** | Not shell-only (UI exists but no logic); not layer-split (BE separate from FE); not tab-split (single tab without context); not horizontal split (one layer across flows) |
| **VS4: Task VS Alignment** (`--with-subtasks` only) | All tasks contribute to VS completion; tasks together deliver the vertical slice; no horizontal-only tasks (unless enabler); task scope stays within VS boundaries |

---

## Epic Quality Checks

| Check | Criteria |
| --- | --- |
| **E1: Vision** | สรุปภาพรวม has problem statement + target users; คุณค่าทางธุรกิจ articulates business value; ลูกค้าเห็นอะไร? present; ความเสี่ยง noted |
| **E2: RICE Score** | Reach estimated; impact scored (0.25–3); confidence percentage; effort in weeks; final score calculated (optional) |
| **E3: Scope** | ขอบเขตงาน covers must-have + should-have + out-of-scope; เงื่อนไขที่ต้องผ่าน lists exit criteria |
| **E4: Task Coverage** | Tasks identified (draft); tasks cover must-have scope; tasks link back to epic |

---

## Blueprint Quality (B1-B8)

Canonical criteria in `blueprint/SKILL.md` — "Blueprint Quality Gate" section.

| Check | Criteria |
| --- | --- |
| **B4a: Performance Goals** | M/L tier: target QPS or concurrent users stated; latency budget defined (p95/p99); data volume projection included. S tier: optional. |

---

## Hierarchy Alignment Checks (`--with-subtasks` only)

> **Principle:** Use only actual fetched data — never guess under any circumstances.
> Hierarchy: Epic → Task (no Story or Subtask level).

| Check | Criteria |
| --- | --- |
| **A1: AC ↔ Task Coverage** | Each epic scope item has ≥1 task backing it; no scope gap; mapping is clear (if unclear → flag) |
| **A2: Service Tag Match** | Epic "ขอบเขตงาน" → all task tags covered; no task tag outside epic scope; tags [BE], [FE-Admin], [FE-Web], [QA] match listed services |
| **A3: Scope Consistency** | Epic in-scope items → task objectives fully covered; no scope gap; no scope creep (task doing more than epic specifies) |
| **A4: Epic ↔ Task Fit** | Task scope falls within epic must-have/should-have; task does not exceed epic scope; skip if task is standalone (no parent epic) |
| **A5: Parent-Child Links** | Every task.parent = epic key (if applicable); no orphan task |
| **A6: Confluence Alignment** | Tech note content consistent with task ACs (if available); tech note does not conflict with task details; skip if no Confluence page exists (flag as info) |

---

## Scoring Guide

### Per Check

| Status | Score | Meaning |
| --- | --- | --- |
| ✅ Pass | 1 | Meets criteria |
| ⚠️ Warning | 0.5 | Partially meets, needs attention |
| ❌ Fail | 0 | Does not meet criteria |

### Overall Score

| Score % | Status | Action |
| --- | --- | --- |
| 90-100% | ✅ Pass | Ready |
| 70-89% | ⚠️ Warning | Review recommended |
| < 70% | ❌ Fail | Must fix before proceeding |

---

## Auto-Fix Capabilities

| Issue | Can Auto-Fix? | How |
| --- | --- | --- |
| Missing code marks | ✅ Yes | Detect paths, add marks |
| Language mixed | ⚠️ Partial | Basic translation |
| Missing Given/When/Then | ❌ No | Requires understanding |
| Wrong heading level | ✅ Yes | Adjust heading attrs.level |
| Missing parent link | ✅ Yes | Add via MCP |

---

## Quick Reference

**Verify Epic + Tasks:** `/verify-issue ABC-XXX --with-subtasks`

**Verify and Auto-Fix:** `/verify-issue ABC-XXX --fix`

**After Full Workflow:** `/create-epic → /verify-issue ABC-XXX --with-subtasks`
