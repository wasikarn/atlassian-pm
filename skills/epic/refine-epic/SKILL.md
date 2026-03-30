---
name: refine-epic
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian]
description: |
  Multi-role debate for refining features and user stories — 3 perspectives challenge each other
  PO (scope/value) × Tech Lead (feasibility/risk + implementation) × QA (edge cases/testability)
  Triggers: "refine epic", "refine feature", "team debate", "3 roles review", "debate requirements", "clarify scope", "unclear scope", "high-risk feature", "multi-role review", "ชัดเจน epic"
  Use when: Epic or feature has unclear scope, high risk, or multi-service changes that need multi-role challenge before writing Jira artifacts
  Do NOT use for: clear-scope Epics ready to write (use create-epic directly); creating individual stories directly without a scope debate (use create-story)
argument-hint: "[feature-description or ABC-XXX]"
effort: medium
---

# /refine-epic

**Mode:** Multi-Role Debate (1 round, 3 perspectives)
**Output:** Refined stories + risks + estimates + test scenarios — ready for `/create-story`

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`
- **Stack:** AdonisJS 5.9 + Effect-TS + Clean Architecture (API) · Next.js 14 + Chakra UI (Website) · Next.js 14 + Tailwind + Headless UI (Admin)

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Gather | `feature_input`, `epic_context`, `existing_issues[]`, `codebase_hints` |
| 2. Propose | `po_proposal`, `tl_assessment`, `qa_scenarios` |
| 3. Converge | `refined_stories[]`, `risks[]`, `estimates`, `out_of_scope[]` |
| 4. QG | `qg_passed`, `qg_fixes[]` |
| 5. Handoff | `next_skill`, `debate_summary` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels, ITERATE cycle.

## Phases

### 1. Gather Context

| Input | Action |
|-------|--------|
| Jira key (ABC-XXX) | `cache_get_issue` → read narrative, ACs, epic context |
| Feature text | Capture as-is |
| Epic key | Read overview + existing children via `cache_search` |

> **🟢 PARALLEL** — Steps 1, 2, and 3 have no dependency on each other. Launch simultaneously (single message, 3 calls): `cache_get_issue` + `cache_similar_issues` + `Task(Explore)`. Summarize only after all 3 complete.

1. Read input + parent epic (if exists) — `cache_get_issue(key)` or capture feature text
2. Dedup check: `cache_search` or `cache_similar_issues` for related stories
3. Quick codebase scan: 1 `Task(Explore)` on likely affected services — identify existing patterns, constraints
4. Summarize context into `debate_brief` for all roles (after 1–3 complete)

**⛔ GATE** — Present understanding + affected services to user. DO NOT launch debate without confirmation.

### 2. Round 1: Propose (3 Parallel Agents)

Launch 3 agents **IN PARALLEL** (single message, 3 Task calls). Each proposes independently without seeing others.

**Agent prompts:** See [references/agent-prompts.md](references/agent-prompts.md) — **PO Round 1**, **TL Round 1**, **QA Round 1** sections. Substitute all `{...}` placeholders with full text before launching.

**🟢 AUTO** — Collect all 3 results. Proceed to convergence.

### 3. Converge

**Main session synthesizes** all 3 agent outputs:

#### 1. Refined Stories

Per story:

| Section | Source |
|---------|--------|
| Narrative | PO proposal |
| ACs | PO + QA enhancements + TL specifics |
| Scope | PO + Tech Lead consensus |
| Risks | Tech Lead combined |
| Estimate | SP (Tech Lead) |
| Test Outline | QA scenarios mapped to ACs |
| Out of Scope | Items cut with rationale from debate |

#### 2. Debate Summary Table

| Topic | PO | Tech Lead | QA | Resolution |
|-------|----|-----------|----|------------|
| [item] | [position] | [position] | [position] | [decision] |

Show only **disagreements and their resolutions** — skip topics where all agreed.

#### 3. Consensus Checks

- [ ] All roles agree on MVP scope?
- [ ] Estimates cover all stories with SP assigned?
- [ ] All critical QA edge cases addressed in ACs or explicitly excluded?
- [ ] Dependencies and blocking order documented?
- [ ] VS assignment validated?

If any check fails → flag to user with the disagreement.

**🔄 ITERATE** — Present refined stories + debate summary as plan cards. Ask:

- **Approve** → proceed to QG
- **Annotate** → user specifies which story # and section to revise → re-run **only the affected role agents** (e.g., scope change → PO + Tech Lead only, not all 3) with updated context (max 1 additional round)
- **Another debate round** → repeat full Round 1 with updated context (expensive, use sparingly)

### 4. Quality Gate — Refined Stories

> **🟢 AUTO** — Validate refined stories before handoff. Escalate only if unfixable.

Per story, verify:

| # | Check | Criteria |
|---|-------|----------|
| 1 | AC naming | All ACs use `AC{N}: [Verb] — [Scenario]` format |
| 2 | SP estimate | Story has SP assigned (XS/S/M/L/XL) |
| 3 | VS assignment | Story has VS label (`vs1-*`, `vs2-*`, `vs-enabler`) |
| 4 | QA coverage | At least 1 QA edge case incorporated per story |
| 5 | Testability | All ACs have measurable Given/When/Then (QA verdict = pass) |
| 6 | Out of scope | Deferred items explicitly listed with rationale |

If any check fails → auto-fix from debate context → re-check. Escalate to user only if ambiguous.

> Stories will be formatted per [templates-story.md](../../../references/templates-story.md) when passed to `/create-story`.

### 5. Handoff

```text
## Feature Refined: [Title]
Stories: N refined (M MVP, K deferred)
Total estimate: X-Y SP
Key risks: [top 2-3]
→ /create-story [first-story]     — create first MVP story + subtasks
→ /create-epic [epic-title]     — if epic needed first
→ /search-issues [keywords]     — final dedup check before creating
```

Present each story as a numbered plan card for user to pick creation order.

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[Story Template](../../../references/templates-story.md) · [Writing Style](../../../references/writing-style.md) · [Workflow Patterns](../../../references/workflow-patterns.md) · [Vertical Slice Guide](../../../references/vertical-slice-guide.md) · [Verification Checklist](../../../references/verification-checklist.md) · [Tools](../../../references/tools.md) · [Decision Guide](references/decision-guide.md) · [Examples](references/examples.md)

After refinement: `/create-story` to create in Jira
