---
name: refine-feature
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache-server, mcp-atlassian]
description: |
  Multi-role debate for refining features and user stories — 4 perspectives challenge each other
  PO (scope/value) × Tech Lead (feasibility/risk) × Engineer (implementation/effort) × QA (edge cases/testability)
  Use when: planning new feature, unclear requirements, high-risk stories, or multi-service changes
  Triggers: "refine feature", "team debate", "4 roles review", "PO+TL+Eng+QA", "clarify scope", "high-risk story"
argument-hint: "[feature-description or ABC-XXX]"
---

# /refine-feature

**Mode:** Multi-Role Debate (2 rounds, 4 perspectives)
**Output:** Refined stories + risks + estimates + test scenarios — ready for `/story-full`

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

> **Workflow Patterns:** See [workflow-patterns.md](../shared-references/workflow-patterns.md) for Gate Levels, ITERATE cycle.

## Phases

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed`.

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

> Stories will be formatted per [templates-story.md](../shared-references/templates-story.md) when passed to `/story-full`.

### 5. Handoff

```text
## Feature Refined: [Title]
Stories: N refined (M MVP, K deferred)
Total estimate: X-Y SP
Key risks: [top 2-3]
→ /story-full [first-story]     — create first MVP story + subtasks
→ /create-epic [epic-title]     — if epic needed first
→ /search-issues [keywords]     — final dedup check before creating
```

Present each story as a numbered plan card for user to pick creation order.

---

## When to Use vs Skip

| Situation | Use `/refine-feature`? | Alternative |
|-----------|----------------------|-------------|
| New feature, unclear scope | **Yes** | — |
| Multi-service feature (BE+FE+Admin) | **Yes** | — |
| High-risk or high-visibility | **Yes** | — |
| Simple bug fix / UI tweak | **No** | `/create-task` or `/story-full` directly |
| Requirements already detailed | **No** | `/story-full` directly |
| Single-service, obvious approach | **No** | `/story-full` directly |

**Token budget:** ~60-80K tokens (8 subagent calls + main session). Justify by reduced rework during implementation.

---

## Example

**Input:** "ระบบ waiting list สำหรับ class ที่เต็ม"

**Round 1 highlights:**

| Role | Key Points |
|------|-----------|
| PO | 3 stories: join waitlist, notification, auto-enroll. VS: `vs2-waitlist-e2e` |
| Tech Lead | New `WaitingListEntry` entity + Effect service. Race condition risk. L estimate |
| Engineer | Reuse `BookingService` patterns. Optimistic locking for concurrency. 16h total |
| QA | "2 notified, 1 slot?" + "class cancelled while on waitlist?" + "already booked other class same time?" |

**Round 2 highlights:**

| Debate | Resolution |
|--------|-----------|
| PO wanted auto-enroll in MVP | **Cut** — Tech Lead flagged complexity, Engineer agreed (8h extra) |
| Tech Lead estimated L (5 SP) | **Revised to M+L** — Engineer proposed splitting join (M) vs notify (L) |
| QA's concurrent claim scenario | **Added to AC** — Engineer confirmed optimistic locking handles it |
| QA's "class cancelled" edge case | **Added new AC** — PO agreed it's MVP-critical |

**Output:**

- Story 1: `[FE-Web] - เข้าร่วม waiting list เมื่อ class เต็ม (Join Waiting List)` — M (3 SP)
  - AC1: Display — แสดงปุ่ม "Join Waiting List" เมื่อ class เต็ม
  - AC2: Join — กดเข้าร่วม แล้วแสดง position ใน queue
  - AC3: Concurrent — 2 คนกดพร้อมกัน ได้ position ถูกต้องไม่ซ้ำ
  - AC4: Cancel — ยกเลิก waitlist แล้ว position คนอื่นเลื่อนขึ้น
- Story 2: `[BE] - แจ้งเตือนเมื่อมี slot ว่าง (Waitlist Notification)` — L (5 SP)
  - AC1: Notify — แจ้งคนแรกใน queue เมื่อมีคน cancel booking
  - AC2: Timeout — ถ้าไม่ confirm ภายใน 30 นาที ส่งต่อคนถัดไป
  - AC3: Class Cancelled — แจ้งทุกคนใน waitlist ว่า class ถูกยกเลิก
- **Out of scope:** Auto-enrollment (deferred to vs3)
- **Dependency:** Notification service must be ready before Story 2

→ `/story-full` Story 1 first (no dependency)

---

## References

- [Story Template](../shared-references/templates-story.md) — Story ADF template (used by `/story-full` downstream)
- [Writing Style](../shared-references/writing-style.md) — Thai + transliteration, concise, scan-first
- [Workflow Patterns](../shared-references/workflow-patterns.md) — Gate levels, ITERATE cycle
- [Vertical Slice Guide](../shared-references/vertical-slice-guide.md) — VS patterns, labels
- [Verification Checklist](../shared-references/verification-checklist.md) — Quality criteria
- [Tools](../shared-references/tools.md) — Jira/Confluence tool selection
- After refinement: `/story-full` to create in Jira
