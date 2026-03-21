# Verification Checklist

> Standard checklists for verifying Jira issues

---

## Technical Checks (All Issue Types)

| Check | Criteria |
| --- | --- |
| **T1: ADF Format** | type: "doc"; version: 1; content array exists; no malformed nodes |
| **T2: Panel Structure** | valid panelType (info, success, warning, error, note); panel content is array; no nested tables in panels |
| **T3: Inline Code Marks** | file paths marked (e.g., `app/Models/User.ts`); API routes marked (e.g., `/api/v1/credits`); component names marked; technical terms marked appropriately |
| **T4: Links** | parent link exists (sub-tasks); epic link exists (stories); child count matches (parents); external links valid |
| **T5: Required Fields** | summary filled; description not empty; issue type correct; project key correct ({{PROJECT_KEY}}); assignee/reporter set (if required) |

---

## Story Quality Checks

| Check | Criteria |
| --- | --- |
| **S1: INVEST** | Independent (no story deps to deliver value); Negotiable (room for discussion); Valuable (clear business value); Estimable (effort can be estimated); Small (1 sprint); Testable (all ACs verifiable) |
| **S2: Narrative Format** | Has "As a [persona]"; "I want to [action]"; "So that [benefit]"; persona is specific (not generic "user"); benefit is business value (not technical) |
| **S3: Narrative Anti-Patterns** | No generic persona ("user" → specify role+situation); no solution masking ("I want a modal" → write goal); "So that" states real value (not restatement); no kitchen sink (1 story ≠ 3 goals — split with SPIDR); no tech story ("As a developer, I want to refactor" → use Task); no copy-paste; persona has role+context+level; goal has verb+object+context; benefit is measurable > behavioral > qualitative |
| **S4: Acceptance Criteria** | All ACs have Given/When/Then clauses; ACs are specific and measurable; cover happy path; cover error cases; ACs are independent |
| **S5: Scope Definition** | Services impacted listed; in-scope clearly defined; out-of-scope mentioned; dependencies noted |
| **S6: Language** | Thai language for content; English for technical terms (transliteration); consistent throughout; no machine translation artifacts |

---

## Vertical Slice Quality Checks

| Check | Criteria |
| --- | --- |
| **VS1: Slice Integrity** | Story delivers end-to-end user value; all required layers touched (UI → API → DB or subset); story is independently deployable; story is testable without other slices |
| **VS2: Labeling (MANDATORY)** | Has feature label (e.g., coupon-web, credit-topup); has VS label (e.g., vs1-skeleton, vs2-credit-e2e, vs-enabler); label matches pattern: `vs{N}-{name}` for numbered, `vs-enabler` for shared, `{feature}-{scope}` for cross-cutting |
| **VS3: Anti-patterns** | Not shell-only (UI exists but no logic); not layer-split (BE separate from FE); not tab-split (single tab without context); not horizontal split (one layer across flows) |
| **VS4: Subtask VS Alignment** (`--with-subtasks` only) | All subtasks contribute to VS completion; subtasks together deliver the vertical slice; no horizontal-only subtasks (unless enabler); subtask scope stays within VS boundaries |

---

## Sub-task Quality Checks

| Check | Criteria |
| --- | --- |
| **ST1: Objective** | Clear 1-2 sentence objective; answers "what" and "why"; specific to this sub-task |
| **ST2: Scope & Files** | File paths are real (not generic — Glob-validated); scope table uses Action\|File format (CREATE/MODIFY/REF); ≥1 REF row exists (pattern reference); config/enum MODIFY included if new value added; no orphan scope item (every file appears in ≥1 AC) |
| **ST3: Acceptance Criteria** | Given/When/Then format; references real method names or endpoints (not generic "call API"); HTTP status codes specified where applicable (201, 409, 403, 204…); error UI specified (toast color + exact message); auth middleware documented if new route added; data contract specified for API subtasks |
| **ST4: Tag & Summary** | Tag matches service: [BE], [FE-Admin], [FE-Web]; summary is descriptive; summary starts with tag |
| **ST5: Language** | Thai + transliteration consistent; technical terms in English; code/paths in English |

---

## QA Sub-task Quality Checks

| Check | Criteria |
| --- | --- |
| **QA1: Coverage** | All story ACs have test coverage; happy path covered; edge cases covered; error handling covered |
| **QA2: Test Format** | Test objective clear; preconditions stated; steps are specific; expected results defined; actual result field (for execution) |
| **QA3: Test Scenarios** | Grouped by type (happy, edge, error); priority assigned; panel colors match: success=happy path, warning=edge cases, error=error handling |
| **QA4: Test Data** | Test data requirements listed; preconditions for tests defined; environment requirements noted |
| **QA5: Language** | Thai + transliteration consistent; technical terms in English; clear, actionable language |

---

## Epic Quality Checks

| Check | Criteria |
| --- | --- |
| **E1: Vision** | Problem statement clear; target users defined; business value articulated; success metrics defined |
| **E2: RICE Score** | Reach estimated; impact scored (0.25–3); confidence percentage; effort in weeks; final score calculated |
| **E3: Scope** | Must-have features listed; should-have features listed; nice-to-have features listed; out-of-scope defined |
| **E4: User Stories** | Stories identified (draft); stories cover must-have scope; stories are independent |

---

## Blueprint Quality (B1-B8)

Canonical criteria in `blueprint/SKILL.md` — "Blueprint Quality Gate" section.

---

## Hierarchy Alignment Checks (`--with-subtasks` only)

> **Principle:** Use only actual fetched data — never guess under any circumstances.
> If unsure which AC maps to which subtask → flag as "unclear mapping"

| Check | Criteria |
| --- | --- |
| **A1: AC ↔ Subtask Coverage** | Each story AC has ≥1 subtask backing it; no AC without a subtask to implement it; mapping is clear (if unclear → flag) |
| **A2: Service Tag Match** | Story "Services Impacted" → all subtask tags covered; no subtask tag outside story scope; tags [BE], [FE-Admin], [FE-Web] match listed services |
| **A3: Scope Consistency** | Story in-scope items → subtask objectives fully covered; no scope gap (items in story but no subtask implements them); no scope creep (subtask doing more than story specifies) |
| **A4: Epic ↔ Story Fit** | Story scope falls within epic must-have/should-have; story does not exceed epic scope; skip if story is standalone (no parent epic) |
| **A5: Parent-Child Links** | Every subtask.parent = story key; story.parent = epic key (if applicable); no orphan subtask |
| **A6: Confluence Alignment** | Tech note content consistent with story ACs (if available); tech note does not conflict with subtask details; skip if no Confluence page exists (flag as info) |

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
| Missing panel | ✅ Yes | Wrap in appropriate panel |
| Wrong panel color | ✅ Yes | Change panelType |
| Missing parent link | ✅ Yes | Add via MCP |

---

## Quick Reference

**Verify Story + Sub-tasks:** `/verify-issue ABC-XXX --with-subtasks`

**Verify and Auto-Fix:** `/verify-issue ABC-XXX --fix`

**After Full Workflow:** `/create-story → /verify-issue ABC-XXX --with-subtasks`
