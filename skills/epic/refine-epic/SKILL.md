---
name: refine-epic
disable-model-invocation: true
context: fork
x-compatibility: [atlassian-cache, mcp-atlassian]
description: |
  Multi-role debate for refining features and user stories — 4 perspectives challenge each other
  PO (scope/value) × Tech Lead (feasibility/risk) × Engineer (implementation/effort) × QA (edge cases/testability)
  Use when: planning new feature, unclear requirements, high-risk stories, or multi-service changes
  Triggers: "refine feature", "team debate", "4 roles review", "PO+TL+Eng+QA", "clarify scope", "high-risk story"
argument-hint: "[feature-description or ABC-XXX]"
---

# /refine-epic

**Mode:** Multi-Role Debate (2 rounds, 4 perspectives)
**Output:** Refined stories + risks + estimates + test scenarios — ready for `/create-story`

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`
- **Stack:** AdonisJS 5.9 + Effect-TS + Clean Architecture (API) · Next.js 14 + Chakra UI (Website) · Next.js 14 + Tailwind + Headless UI (Admin)

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Gather | `feature_input`, `epic_context`, `existing_issues[]`, `codebase_hints` |
| 2. Propose | `po_proposal`, `tl_assessment`, `eng_approach`, `qa_scenarios` |
| 3. Challenge | `po_revised`, `tl_verdict`, `eng_verdict`, `qa_verdict` |
| 4. Converge | `refined_stories[]`, `risks[]`, `estimates`, `out_of_scope[]` |
| 4d. QG | `qg_passed`, `qg_fixes[]` |
| 5. Handoff | `next_skill`, `debate_summary` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels, ITERATE cycle.

## Phases

### 1. Gather Context

**Input types:**

| Input | Action |
|-------|--------|
| Jira key (ABC-XXX) | `cache_get_issue` → read narrative, ACs, epic context |
| Feature text | Capture as-is |
| Epic key | Read overview + existing children via `cache_search` |

**Actions:**

1. Read input + parent epic (if exists)
2. Dedup check: `cache_search` or `cache_similar_issues` for related stories
3. Quick codebase scan: 1 `Task(Explore)` on likely affected services — identify existing patterns, constraints
4. Summarize context into `debate_brief` for all roles

**⛔ GATE** — Present understanding + affected services to user. DO NOT launch debate without confirmation.

### 2. Round 1: Propose (4 Parallel Agents)

Launch 4 agents **IN PARALLEL** (single message, 4 Task calls). Each proposes independently without seeing others.

**Agent prompts:** See [references/agent-prompts.md](references/agent-prompts.md) — **PO Round 1**, **TL Round 1**, **Engineer Round 1**, **QA Round 1** sections. Substitute all `{...}` placeholders with full text before launching.

**🟢 AUTO** — Collect all 4 results. Proceed to Round 2.

### 3. Round 2: Challenge (4 Parallel Agents)

Share **ALL Round 1 outputs** to each agent. Launch 4 agents **IN PARALLEL**.

Each agent now **challenges the others** based on their expertise.

**Agent prompts:** See [references/agent-prompts.md](references/agent-prompts.md) — **PO Round 2**, **TL Round 2**, **Engineer Round 2**, **QA Round 2** sections. Substitute all `{...}` placeholders with full text before launching.

**🟢 AUTO** — Collect all 4 results. Proceed to convergence.

### 4. Converge

**Main session synthesizes** all 8 agent outputs (Round 1 + Round 2):

#### 4a. Refined Stories

Per story:

| Section | Source |
|---------|--------|
| Narrative | PO revised (Round 2) |
| ACs | PO + QA enhancements + Engineer specifics |
| Scope | PO + Tech Lead consensus |
| Risks | Tech Lead + Engineer combined |
| Estimate | SP (Tech Lead) + Hours (Engineer) |
| Test Outline | QA scenarios mapped to ACs |
| Out of Scope | Items cut with rationale from debate |

#### 4b. Debate Summary Table

| Topic | PO | Tech Lead | Engineer | QA | Resolution |
|-------|----|-----------|----------|----|------------|
| [item] | [position] | [position] | [position] | [position] | [decision] |

Show only **disagreements and their resolutions** — skip topics where all agreed.

#### 4c. Consensus Checks

- [ ] All roles agree on MVP scope?
- [ ] Estimate variance < 2x between Tech Lead and Engineer?
- [ ] All critical QA edge cases addressed in ACs or explicitly excluded?
- [ ] Dependencies and blocking order documented?
- [ ] VS assignment validated?

If any check fails → flag to user with the disagreement.

**🔄 ITERATE** — Present refined stories + debate summary as plan cards. Ask:

- **Approve** → proceed to QG
- **Annotate** → user specifies which story # and section to revise → re-run **only the affected role agents** (e.g., scope change → PO + Tech Lead only, not all 4) with updated context (max 2 rounds)
- **Another debate round** → repeat full Round 2 with updated context (expensive, use sparingly)

### 4d. Quality Gate — Refined Stories

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

---

## When to Use vs Skip

> See [references/decision-guide.md](references/decision-guide.md) for when to use this skill vs alternatives.

---

## Examples

### ✅ Good

```text
/refine-epic "User onboarding flow with email verification"   # clear description → all 4 roles have grounded context
/refine-epic {{PROJECT_KEY}}-55                                           # story/epic key → reads ACs, epic context, dedup check before debate
/refine-epic "Payment retry logic with idempotency keys"      # high-risk, multi-service → 4-role debate catches edge cases early
/refine-epic {{PROJECT_KEY}}-55 "focus on edge cases for concurrent sessions"  # scoped hint directs QA + TL agents to specific risk area
```

### ❌ Bad

```text
/refine-epic                                                  # no input → debate brief is empty, all 4 roles produce generic output
/refine-epic "fix the login bug"                              # too vague and too small — use /create-task or just fix it directly
/refine-epic {{PROJECT_KEY}}-55                                           # running after stories are already in Jira — debate output won't retroactively update created issues
/refine-epic "everything in the Q2 roadmap"                   # scope too broad — refine one feature or story at a time for useful output
```

**Common mistakes:**

- Using refine-epic after stories already exist in Jira — the workflow produces refined story cards for `/create-story`; running it post-creation creates a parallel set of stories you then have to reconcile manually.
- Passing a feature description so vague that Phase 1 gate blocks — "improve performance" gives no domain, no affected service, no user scenario. The gate will block; you'll spend turns just scoping the question.
- Treating the debate summary as the final output and skipping `/create-story` — the refined stories are plan cards, not Jira issues. Nothing is in Jira until you explicitly call `/create-story`.
- Annotating a story mid-debate without specifying which section to revise — "change story 2" forces all 4 agents to re-run; "change story 2 ACs only" re-runs PO + QA only, saving tokens.

## Example

> See [references/examples.md](references/examples.md) for a full Round 1 and Round 2 debate example with output stories.

---

## References

- [Story Template](../../../references/templates-story.md) — Story ADF template (used by `/create-story` downstream)
- [Writing Style](../../../references/writing-style.md) — Thai + transliteration, concise, scan-first
- [Workflow Patterns](../../../references/workflow-patterns.md) — Gate levels, ITERATE cycle
- [Vertical Slice Guide](../../../references/vertical-slice-guide.md) — VS patterns, labels
- [Verification Checklist](../../../references/verification-checklist.md) — Quality criteria
- [Tools](../../../references/tools.md) — Jira/Confluence tool selection
- [Decision Guide](references/decision-guide.md)
- [Examples](references/examples.md)
- After refinement: `/create-story` to create in Jira
