---
name: create-story
disable-model-invocation: true
description: |
  Create a new User Story from requirements with a 5-phase PO workflow
  Use when creating a new story, have a feature request, or need to convert requirements into a story
argument-hint: "[story-description]"
---

# /create-story

**Role:** Senior Product Owner
**Output:** User Story in Jira with ADF format

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Discovery | `epic_data`, `vs_assignment`, `user_requirements`, `user_context` |
| 2. Write Story | `story_narrative`, `acs[]`, `scope`, `dod` |
| 3. INVEST | `invest_score`, `vs_validated` |
| 4. QG | `qg_score`, `passed_qg` |
| 5. Create | `story_key` ({{PROJECT_KEY}}-XXX) |

> **Workflow Patterns:** See [workflow-patterns.md](../shared-references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.

### 1. Discovery

- If Epic exists → `MCP: jira_get_issue` to read context + VS plan + Problem narrative
- Ask user: Who? What? Why? Constraints?
  - **Story Context:** What is the user currently doing? What's difficult? (for 📍 context line)
- **VS Assignment:** Which vertical slice does this story belong to? (`vs1-skeleton`, `vs2-*`, `vs-enabler`)
- **⛔ GATE — DO NOT PROCEED** without user confirmation of requirements + VS assignment.

### 2. Write Story

```text
📍 [User's current situation — what they're doing, what's difficult]  ⚡ optional
As a [persona],
I want to [action],
So that [benefit].
```

- ⚡ **Context line:** Include when persona is new or workflow is complex — not needed for every story
- Define ACs: Given/When/Then format
- **AC Naming:** Use `AC{N}: [Verb] — [Scenario Name]` (not just "AC1: Title")
- Specify Scope (affected services) and DoD
- **VS Check:** Story delivers end-to-end value? All layers touched? (not shell-only or layer-split)
- Use Thai + transliteration
- **🔄 ITERATE** — Present story draft as plan card (narrative, ACs, scope, DoD). Ask: Approve / Annotate / Major rework.
  - Annotate → user specifies items to change → revise ONLY those items → re-present (max 3 rounds)
  - Approve → proceed to INVEST validation
  - Major rework → back to Discovery
  - See [Annotation Cycle](../shared-references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 3. INVEST + VS Validation

| ✓ | Criteria | Question |
| --- | --- | --- |
| | Independent | Not dependent on other stories? |
| | Negotiable | Room for discussion? |
| | Valuable | Clear business value? |
| | Estimable | Can estimate effort? |
| | **Small + Vertical** | Completable in 1 sprint? **End-to-end slice?** |
| | Testable | All ACs verifiable in isolation? |

**VS Anti-pattern Check:**

- ❌ Shell-only (UI has no logic) → Add minimal happy path
- ❌ Layer-split (BE separated from FE) → Combine into single story
- ❌ Tab-split → Split by business rule instead

**🟢 AUTO** — Validate all criteria. If any fail or VS anti-pattern detected → auto-fix and re-validate. Escalate to user only if unfixable.

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send Story to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](../shared-references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Story Quality X/6 | Overall X%`

### 5. Create in Jira

> **🟢 AUTO** — If QG passed → create automatically. No user interaction needed.

```bash
acli jira workitem create --from-json tasks/story.json
```

- ADF: Info panel (narrative) + Success panels (ACs)
- **Labels (MANDATORY):**
  - Feature label: `coupon-web`, `credit-topup`, etc.
  - VS label: `vs1-skeleton`, `vs2-credit-e2e`, `vs-enabler`, etc.
  - See convention: [Vertical Slice Guide](../shared-references/vertical-slice-guide.md)

> **🟢 AUTO** — HR6: `cache_invalidate(story_key)` after create.

**Set estimation fields (after create):**

```text
MCP: jira_update_issue(issue_key="{{PROJECT_KEY}}-XXX", additional_fields={
  "customfield_10016": <SP>,                  # Story Points (XS=1,S=2,M=3,L=5,XL=8)
  "customfield_10107": {"value": "<SIZE>"},   # Size (XS/S/M/L)
  "{{START_DATE_FIELD}}": "YYYY-MM-DD",          # Start Date
  "duedate": "YYYY-MM-DD"                     # Due Date
})
```

> **🟢 AUTO** — HR6: `cache_invalidate(story_key)` after field update.

### 6. Handoff

```text
## Story Created: [Title] ({{PROJECT_KEY}}-XXX)
ACs: N | Scope: [services]
→ Use /analyze-story {{PROJECT_KEY}}-XXX to continue
```

---

## Example

**Input:** "สร้าง story สำหรับ admin filter coupon by status"

**Output:**

- Story `BEP-2468`: [FE-Admin] - เพิ่ม filter coupon ตาม status (Coupon Status Filter)
- AC1: Display — แสดง filter options (active/inactive/expired) บน coupon list
- AC2: Filter — กดเลือก status แล้วแสดงเฉพาะ coupon ที่ตรง
- AC3: Reset — กด clear filter แล้วกลับมาแสดงทั้งหมด
- VS: `vs1-coupon-filter` | Size: S (2 SP)

---

## References

- [ADF Core Rules](../shared-references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Story Template](../shared-references/templates-story.md) - Story ADF template + best practices
- [Vertical Slice Guide](../shared-references/vertical-slice-guide.md) - VS patterns, labels, DoD
- [Verification Checklist](../shared-references/verification-checklist.md) - INVEST, AC quality
- After creation: `/verify-issue {{PROJECT_KEY}}-XXX`
