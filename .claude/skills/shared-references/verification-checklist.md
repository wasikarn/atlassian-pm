# Verification Checklist

> Standard checklists for verifying Jira issues

---

## Technical Checks (All Issue Types)

### T1: ADF Format

```text
□ Description has type: "doc"
□ Version is 1
□ Content array exists
□ No malformed nodes
```

### T2: Panel Structure

```text
□ Panels have valid panelType (info, success, warning, error, note)
□ Panel content is array
□ No nested tables in panels
```

### T3: Inline Code Marks

```text
□ File paths have code marks (e.g., `app/Models/User.ts`)
□ API routes have code marks (e.g., `/api/v1/credits`)
□ Component names have code marks (e.g., `CreditHistoryPage`)
□ Technical terms marked appropriately
```

### T4: Links

```text
□ Parent link exists (for sub-tasks)
□ Epic link exists (for stories)
□ Child count matches (for parents)
□ External links valid (Confluence, docs)
```

### T5: Required Fields

```text
□ Summary filled
□ Description not empty
□ Issue type correct
□ Project key correct (BEP)
□ Assignee/Reporter set (if required)
```

---

## Story Quality Checks

### S1: INVEST Criteria

```text
□ Independent - Does not depend on other stories to deliver value
□ Negotiable - Has room for discussion
□ Valuable - Has clear business value
□ Estimable - Effort can be estimated
□ Small - Can be completed in 1 sprint
□ Testable - All ACs can be verified
```

### S2: Narrative Format

```text
□ Has "As a [persona]"
□ Has "I want to [action]"
□ Has "So that [benefit]"
□ Persona is specific (not generic "user")
□ Benefit is business value (not technical)
```

### S3: Narrative Anti-Patterns

```text
□ No Generic Persona ("As a user" → must specify role + situation)
□ No Solution Masking ("I want a modal" → write goal, solution goes in AC)
□ No Missing Why ("So that" states real value, not restatement of goal)
□ No Kitchen Sink (1 story ≠ 3 goals — split with SPIDR)
□ No Tech Story ("As a developer, I want to refactor" → use Task)
□ No Copy-Paste (each story has unique context)
□ Persona has role + context + level (not just "admin")
□ Goal has verb + object + context (not just "see list")
□ Benefit is business value: measurable > behavioral > qualitative
```

### S4: Acceptance Criteria

```text
□ All ACs have Given clause
□ All ACs have When clause
□ All ACs have Then clause
□ ACs are specific (not vague)
□ ACs are measurable
□ ACs cover happy path
□ ACs cover error cases
□ ACs are independent
```

### S5: Scope Definition

```text
□ Services impacted listed
□ In-scope clearly defined
□ Out-of-scope mentioned
□ Dependencies noted
```

### S6: Language

```text
□ Thai language for content
□ English for technical terms (transliteration)
□ Consistent throughout
□ No machine translation artifacts
```

---

## Vertical Slice Quality Checks

### VS1: Slice Integrity

```text
□ Story delivers end-to-end user value
□ All required layers touched (UI → API → DB or subset)
□ Story is independently deployable
□ Story is testable without other slices
```

### VS2: Labeling (MANDATORY)

```text
□ Has feature label (e.g., coupon-web, credit-topup)
□ Has VS label (e.g., vs1-skeleton, vs2-credit-e2e, vs-enabler)
□ Label matches VS pattern:
  - vs{N}-{name} for numbered slices
  - vs-enabler for shared components
  - {feature}-{scope} for cross-cutting
```

### VS3: Anti-patterns Check

```text
□ Not shell-only (UI exists but no logic)
□ Not layer-split (BE separate from FE)
□ Not tab-split (single tab without context)
□ Not horizontal split (one layer across flows)
```

### VS4: Subtask VS Alignment (`--with-subtasks` only)

```text
□ All subtasks contribute to VS completion
□ Subtasks together deliver the vertical slice
□ No horizontal-only subtasks (unless enabler)
□ Subtask scope stays within VS boundaries
```

---

## Sub-task Quality Checks

### ST1: Objective

```text
□ Clear 1-2 sentence objective
□ Answers "what" and "why"
□ Specific to this sub-task
```

### ST2: Scope & Files

```text
□ File paths are real (not generic — Glob-validated)
□ Scope table uses Action|File format (CREATE / MODIFY / REF)
□ At least 1 REF row exists (pattern reference for developer)
□ Config/enum MODIFY included if new value is added
□ No orphan scope item (every file must appear in at least 1 AC)
```

### ST3: Acceptance Criteria

```text
□ Given/When/Then format
□ References real method names or endpoints (not generic "call API")
□ HTTP status codes specified where applicable (201, 409, 403, 204...)
□ Error UI specified (toast color + exact message text)
□ Auth middleware documented if new route added
□ Data contract specified for API subtasks
```

### ST4: Tag & Summary

```text
□ Tag matches service: [BE], [FE-Admin], [FE-Web]
□ Summary is descriptive
□ Summary starts with tag
```

### ST5: Language

```text
□ Thai + transliteration consistent
□ Technical terms in English
□ Code/paths in English
```

---

## QA Sub-task Quality Checks

### QA1: Coverage

```text
□ All Story ACs have test coverage
□ Happy path covered
□ Edge cases covered
□ Error handling covered
```

### QA2: Test Format

```text
□ Test objective clear
□ Preconditions stated
□ Steps are specific
□ Expected results defined
□ Actual result field (for execution)
```

### QA3: Test Scenarios

```text
□ Scenarios grouped by type (happy, edge, error)
□ Priority assigned to each test
□ Panel colors match type:
  - 🟢 success = Happy path
  - 🟡 warning = Edge cases
  - 🔴 error = Error handling
```

### QA4: Test Data

```text
□ Test data requirements listed
□ Preconditions for tests defined
□ Environment requirements noted
```

### QA5: Language

```text
□ Thai + transliteration consistent
□ Technical terms in English
□ Clear, actionable language
```

---

## Epic Quality Checks

### E1: Vision

```text
□ Problem statement clear
□ Target users defined
□ Business value articulated
□ Success metrics defined
```

### E2: RICE Score

```text
□ Reach estimated
□ Impact scored (0.25-3)
□ Confidence percentage
□ Effort in weeks
□ Final score calculated
```

### E3: Scope

```text
□ Must-have features listed
□ Should-have features listed
□ Nice-to-have features listed
□ Out-of-scope defined
```

### E4: User Stories

```text
□ Stories identified (draft)
□ Stories cover must-have scope
□ Stories are independent
```

---

## Blueprint Quality Checks

### B1: Executive Summary

```text
□ 1 paragraph (not bullet list)
□ Mentions problem being solved
□ Mentions proposed solution
□ Mentions who benefits
```

### B2: Business Case

```text
□ Problem narrative present
□ ≥2 user scenarios with persona + goal + outcome
□ Non-goals / no-gos listed
□ Appetite defined (sprints or effort range)
□ Success metrics defined
```

### B3: Domain Analysis

```text
□ ≥1 bounded context identified
□ ≥1 domain event mapped (Command → Event)
□ Entities have key attributes listed
□ Aggregates have invariants defined
□ Context map shows integration patterns
```

### B4: Architecture & Design

```text
□ Alternatives Considered has ≥2 options
□ Each option has pros and cons
□ Chosen approach has explicit rationale
□ New services/patterns documented
□ Migration complexity assessed
```

### B5: Technical Specification

```text
□ File paths are real (Glob-validated, not generic)
□ Endpoints have HTTP methods + status codes
□ Data contracts specified (request/response)
□ DB changes documented (tables, columns, constraints)
□ Code reuse opportunities identified
```

### B6: Risks & Edge Cases

```text
□ ≥3 risks with severity + mitigation
□ ≥2 edge cases documented
□ Rabbit holes identified
□ Open questions listed with owners
□ No unresolved "blocker" questions
```

### B7: Test Strategy

```text
□ Test approach per affected layer
□ ≥3 critical test scenarios
□ Happy path + unhappy path covered
□ Performance/security test needs assessed
```

### B8: Delivery Plan

```text
□ VS plan exists with slice labels
□ Stories mapped to VS labels
□ Sprint estimate present
□ Dependency ordering documented
□ Team assignment suggestions (if applicable)
```

---

## Hierarchy Alignment Checks (`--with-subtasks` only)

> **Principle:** Use only actual fetched data — never guess under any circumstances.
> If unsure which AC maps to which subtask → flag as "unclear mapping"

### A1: AC ↔ Subtask Coverage

```text
□ Each Story AC has ≥1 subtask backing it
□ No AC without a subtask to implement it
□ Mapping is clear (if unclear → flag)
```

### A2: Service Tag Match

```text
□ Story "Services Impacted" → all subtask tags covered
□ No subtask tag outside Story scope
□ Tags: [BE], [FE-Admin], [FE-Web] match the listed services
```

### A3: Scope Consistency

```text
□ Story in-scope items → subtask objectives fully covered
□ No scope gap (items in Story but no subtask implements them)
□ No scope creep (subtask doing more than Story specifies)
```

### A4: Epic ↔ Story Fit

```text
□ Story scope falls within Epic must-have/should-have
□ Story does not exceed Epic scope
□ Skip if Story is standalone (no parent Epic)
```

### A5: Parent-Child Links

```text
□ Every subtask.parent = Story key
□ Story.parent = Epic key (if applicable)
□ No orphan subtask
```

### A6: Confluence Alignment

```text
□ Tech Note content is consistent with Story ACs (if available)
□ Tech Note does not conflict with subtask details
□ Skip if no Confluence page exists, flag as info
```

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

### Verify Story + Sub-tasks

```text
/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks
```

### Verify and Auto-Fix

```text
/verify-issue {{PROJECT_KEY}}-XXX --fix
```

### After Full Workflow

```text
/story-full → /verify-issue {{PROJECT_KEY}}-XXX --with-subtasks
```
