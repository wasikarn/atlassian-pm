---
name: create-epic
disable-model-invocation: true
x-compatibility: [jira-cache-server, mcp-atlassian, mcp-confluence, acli]
description: |
  Create Epic + Epic Doc from product vision with a 5-phase PM workflow
  Use when creating a new initiative, have a product vision, or need RICE prioritization

  Triggers: "create epic", "new epic", "new initiative", "product vision", "RICE"
argument-hint: "[epic-title]"
---

# /create-epic

**Role:** Senior Product Manager
**Output:** Epic in Jira + Epic Doc in Confluence

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 0. Blueprint (optional) | `blueprint_page_id`, `blueprint_url`, `blueprint_stories[]` |
| 1. Discovery | `stakeholder_input`, `problem_narrative`, `vs_plan`, `user_requirements` |
| 2. RICE | `rice_score`, `priority` |
| 3. Scope | `scope_items[]`, `vs_stories[]`, `mvp_definition` |
| 4. QG | `qg_score`, `passed_qg` |
| 5. Create | `epic_key`, `epic_doc_id` |

> **Workflow Patterns:** See [workflow-patterns.md](../../shared-references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Blueprint Handoff Check

> **Check first:** ดู conversation history ว่ามี `/feature-blueprint` output หรือไม่

**If `blueprint_backlog_map` is present in history:**

Extract from blueprint output:

- `epic.title` → ใช้เป็น epic title (ข้ามการถามจาก user)
- `stories[]` → เก็บเป็น `vs_stories[]` สำหรับ Phase 3
- `non_goals[]` → เก็บเป็น out-of-scope items สำหรับ Phase 3 scope definition
- `blueprint_page_id` → link ใน Epic Doc section "References"

Skip interview questions in Phase 1 for information already documented.
แสดง summary ให้ user confirm:
> "พบ blueprint: [Feature Name] — ใช้ข้อมูลจาก blueprint สำหรับ epic นี้ confirm?"

**⛔ GATE** — รอ user confirm ก่อนดำเนินต่อ

**If no blueprint in history:** ดำเนิน Phase 1 Discovery ปกติ

---

## Phases

### 1. Discovery

- Interview stakeholder:
  - **Problem narrative:** What is the current situation? What is the problem? What happens if we don't act?
  - Target users? Business value? Success metrics?
- If existing docs available → read context
- **Narrative Arc:** Summarize as `[Current situation] → [Problem] → [This Epic solves it by...]`
- **VS Planning:** Identify potential vertical slices (what distinct user flows exist?)
- **⛔ GATE — DO NOT PROCEED** without stakeholder confirmation of problem narrative + VS planning.

### 2. RICE Prioritization

- **R**each (1-10): Number of users affected
- **I**mpact (0.25-3): Level of impact on user
- **C**onfidence (0-100%): Confidence in estimate
- **E**ffort (person-weeks): Effort required
- Formula: `(R × I × C) / E`
- **🟡 REVIEW** — Present RICE scoring to stakeholder. Proceed unless stakeholder objects.

### 3. Define Scope + VS Planning

> **If `vs_stories[]` pre-populated from blueprint:** ข้าม VS derivation — ใช้ `vs_stories[]` จาก blueprint โดยตรง แสดงให้ user confirm แทน
> **If `non_goals[]` present from blueprint:** ใช้เป็น out-of-scope items ใน scope definition (ไม่ต้องถามใหม่)

- Identify high-level requirements
- **VS Pattern Selection:** (see [vertical-slice-guide.md](../../shared-references/vertical-slice-guide.md))
  - Walking Skeleton? → `vs1-skeleton`
  - Enablers needed? → `vs-enabler`
  - Business rule splits? → `vs2-*`, `vs3-*`
- Break into User Stories by VS (draft):
  - vs1-skeleton: Story A, Story B
  - vs2-{rule}: Story C, Story D
- Define MVP: Which VS are must-have vs nice-to-have?
- Identify Dependencies and Risks
- **🔄 ITERATE** — Present scope + VS plan + MVP as plan cards (stories grouped by VS, in/out scope). Ask: Approve / Annotate / Major rework.
  - Annotate → stakeholder specifies items to change (add/remove stories, adjust VS, change MVP boundary)
  - Approve → proceed to Quality Gate
  - Major rework → back to Discovery
  - See [Annotation Cycle](../../shared-references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send Epic to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](../../shared-references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Epic Quality X/4 | Overall X%`

### 5. Create Artifacts

> **🟢 AUTO** — If QG passed → create automatically. No user interaction needed.

1. **Epic Doc** → `MCP: confluence_create_page(space_key: "{{PROJECT_KEY}}")`
   - Include VS Map table in Epic Doc
2. **Epic** → `acli jira workitem create --from-json {{artifacts_dir}}/epic.json`
   - Add labels: feature label + `vs-planned`
3. **Link** Epic to Doc

> **🟢 AUTO** — HR6: `cache_invalidate(epic_key)` after create.

### 6. Handoff

```text
## Epic Created: [Title] ({{PROJECT_KEY}}-XXX)
RICE Score: X | Stories: N planned
Epic Doc: [link] | Epic: [link]
→ Use /story-full to continue
```

---

## Epic Structure (ADF)

> See [references/epic-adf-structure.md](references/epic-adf-structure.md) for the full Epic ADF section layout and panel type reference.

---

## Example

> See [references/examples.md](references/examples.md) for a full input/output example.

---

## References

- [ADF Core Rules](../../shared-references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Epic Template](../../shared-references/templates-epic.md) - Epic ADF template + best practices
- [Tool Selection](../../shared-references/tools.md) - Tool selection, effort sizing
- [Vertical Slice Guide](../../shared-references/vertical-slice-guide.md) - VS patterns, decomposition
- [Epic ADF Structure](references/epic-adf-structure.md) - Epic ADF section layout and panel type reference
- [Examples](references/examples.md) - Full input/output example
- After creation: `/verify-issue {{PROJECT_KEY}}-XXX`
