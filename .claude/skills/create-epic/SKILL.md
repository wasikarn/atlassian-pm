---
name: create-epic
disable-model-invocation: true
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
| 1. Discovery | `stakeholder_input`, `problem_narrative`, `vs_plan`, `user_requirements` |
| 2. RICE | `rice_score`, `priority` |
| 3. Scope | `scope_items[]`, `vs_stories[]`, `mvp_definition` |
| 4. QG | `qg_score`, `passed_qg` |
| 5. Create | `epic_key`, `epic_doc_id` |

> **Workflow Patterns:** See [workflow-patterns.md](../shared-references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/ITERATE/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Phases

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed` as you work.

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

- Identify high-level requirements
- **VS Pattern Selection:** (see [vertical-slice-guide.md](../shared-references/vertical-slice-guide.md))
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
  - See [Annotation Cycle](../shared-references/workflow-patterns.md#annotation-cycle-iterate-gate)

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT send Epic to Atlassian without QG ≥ 90%.

> [QG Scoring Rules](../shared-references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Epic Quality X/4 | Overall X%`

### 5. Create Artifacts

> **🟢 AUTO** — If QG passed → create automatically. No user interaction needed.

1. **Epic Doc** → `MCP: confluence_create_page(space_key: "{{PROJECT_KEY}}")`
   - Include VS Map table in Epic Doc
2. **Epic** → `acli jira workitem create --from-json tasks/epic.json`
   - Add labels: feature label + `vs-planned`
3. **Link** Epic to Doc

> **🟢 AUTO** — HR6: `cache_invalidate(epic_key)` after create.

### 6. Handoff

```text
## Epic Created: [Title] ({{PROJECT_KEY}}-XXX)
RICE Score: X | Stories: N planned
Epic Doc: [link] | Epic: [link]
→ Use /create-story to continue
```

---

## Epic Structure (ADF)

| Section | Panel Type | Content |
| --- | --- | --- |
| 🎯 Epic Overview | `info` | Problem statement + summary + scope statement |
| 💰 Business Value | `success` | Revenue, Retention, Operations |
| 📦 Scope | `info` + table | Features/modules breakdown |
| 📊 RICE Score | table | R/I/C/E + final score |
| 🎯 Success Metrics | table | KPIs + targets |
| 📋 User Stories | `info` panels | Grouped by feature area |
| 📈 Progress | `note` | Done/In Progress/To Do counts |
| 🔗 Links | table | Epic Doc, Technical Notes |

**ADF Restrictions:**

- ❌ Do not nest tables inside panels (will error)
- ✅ Use paragraphs or bulletList inside panels instead

---

## Example

**Input:** "สร้าง epic สำหรับระบบ coupon management ทั้งหมด"

**Output:**

- Epic `BEP-2800`: [Platform] - ระบบจัดการ Coupon (Coupon Management System)
  - RICE: R=8 I=7 C=0.8 E=3 → Score 14.9
  - Scope: 5 stories (Create, List, Redeem, Report, Settings)
- Epic Doc: Confluence page with overview, business value, VS plan

---

## References

- [ADF Core Rules](../shared-references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Epic Template](../shared-references/templates-epic.md) - Epic ADF template + best practices
- [Tool Selection](../shared-references/tools.md) - Tool selection, effort sizing
- [Vertical Slice Guide](../shared-references/vertical-slice-guide.md) - VS patterns, decomposition
- After creation: `/verify-issue {{PROJECT_KEY}}-XXX`
