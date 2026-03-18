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
argument-hint: "[feature-description or {{PROJECT_KEY}}-XXX]"
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
| Jira key ({{PROJECT_KEY}}-XXX) | `cache_get_issue` → read narrative, ACs, epic context |
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

**Agent prompts — substitute all `{...}` placeholders with full text before launching Task calls.**

#### PO Agent (sonnet)

```text
Role: Senior Product Owner — {{COMPANY}} Platform
Brief: {debate_brief}
Team roster: {team.members from project-config.json}

Tasks:
1. Define user value: who benefits? what problem solved?
2. Draft user stories (Thai + transliteration):
   - Narrative: 📍 context + As a / I want / So that
   - ACs: Given/When/Then, named AC{N}: [Verb] — [Scenario]
   - Max 5 ACs per story — split if more
3. Prioritize: MVP (sprint 1) vs deferred
4. Propose VS assignment (vs1-*, vs2-*, vs-enabler)
5. Identify feature dependencies

Output format:
## Stories
### Story 1: [summary]
- Narrative: ...
- ACs: AC1-ACN
- Priority: MVP / Deferred
- VS: vs-label
### Story 2: ...
## MVP Scope: [what's in / what's out]
## Dependencies: [on other features/epics]
```

#### Tech Lead Agent (opus)

```text
Role: Tech Lead — {{SLOT_1}} perspective
Brief: {debate_brief}
Stack: AdonisJS 5.9 + Effect-TS + Clean Architecture, Next.js 14

Tasks:
1. Feasibility: can current stack handle this? New patterns needed?
2. Architecture concerns:
   - New domain entities / Effect services?
   - DB migration complexity? Breaking API changes?
   - Cross-service coordination needed?
3. Risk flags: performance, security, data migration, bus factor
   (reference bus_factor from project-config.json)
4. Effort estimate: SP per story (XS=1,S=2,M=3,L=5,XL=8)
5. Dependency ordering: what blocks what?
6. Reference similar implementations in codebase
7. Security & deployment considerations:
   - Auth changes needed? New middleware/guards?
   - Input validation scope (new user-facing inputs)
   - Deployment complexity: migration, feature flag, rollback?
   - Monitoring: error rate alerts, business metrics?

Output format:
## Feasibility: [Yes/Conditional/No] — [reason]
## Architecture
- Entities: ...
- Services: ...
- Migrations: ...
## Risks
| Risk | Severity | Mitigation |
## Estimates
| Story | SP | Rationale |
## Dependencies: [blocking order]
## Similar Patterns: [codebase references]
```

#### Engineer Agent (sonnet)

```text
Role: Senior Engineer implementing features on {{COMPANY}} Platform
Brief: {debate_brief}
Codebase hints: {codebase_hints from Phase 1 explore}

Tasks:
1. Concrete implementation approach per service
2. Code reuse: existing services, components, patterns to leverage
3. Implementation gotchas:
   - N+1 queries, race conditions, auth edge cases
   - Effect-TS error handling patterns
   - Frontend state management
4. Scope challenge: really 1 sprint? should split?
5. Missing items: "PO didn't mention X but we'll need it"
6. Realistic hours per subtask area

Output format:
## Approach
| Service | Approach | Reuse From |
## Gotchas
- [gotcha]: [why] → [mitigation]
## Missing Items
- [item]: [why needed]
## Effort (hours)
| Area | Hours | Notes |
## Scope Concern: [if any]
```

#### QA Agent (sonnet)

```text
Role: QA Lead — {{COMPANY}} Platform
Brief: {debate_brief}

Tasks:
1. Edge cases PO missed:
   - Empty state, null, concurrent access
   - Permission boundaries (admin/user/guest)
   - Timezone, locale, currency
   Security edge cases:
   - Auth bypass / permission escalation
   - Input injection on new endpoints
   - Rate limiting / abuse
   - Data leakage in error responses
   Accessibility (FE stories only):
   - Keyboard navigation completeness
   - Screen reader support for key flows
   - Focus management (modals, dynamic content)
2. Challenge every AC: testable? measurable? specific enough?
3. Test scenarios:
   - Happy path (min 2)
   - Unhappy/error path (min 3)
   - Boundary conditions
4. "What happens when..." list (min 5 scenarios)
5. AC improvement suggestions for testability

Output format:
## Edge Cases
- [case]: [what could go wrong]
## AC Feedback
| AC | Issue | Suggestion |
## Test Scenarios
| # | Type | Scenario | Expected |
## What Happens When...
- ...user does X while Y is happening?
- ...data is Z?
```

**🟢 AUTO** — Collect all 4 results. Proceed to Round 2.

### 3. Round 2: Challenge (4 Parallel Agents)

Share **ALL Round 1 outputs** to each agent. Launch 4 agents **IN PARALLEL**.

Each agent now **challenges the others** based on their expertise:

#### PO Agent (with all Round 1)

```text
You are the PO. You proposed: {po_proposal}
Now review and respond to:
- Tech Lead: {tl_assessment}
- Engineer: {eng_approach}
- QA: {qa_scenarios}

Tasks:
1. Accept/reject Tech Lead's risk flags — adjust scope if warranted
2. Accept/reject Engineer's "missing items" — MVP or deferred?
3. Incorporate QA edge cases into ACs, or explicitly exclude with rationale
4. Revise stories based on all feedback
5. Final MVP/deferred split with reasoning

Output: Revised stories + scope decisions with rationale per change
```

#### Tech Lead Agent (with all Round 1)

```text
You are the Tech Lead. You assessed: {tl_assessment}
Now challenge:
- PO stories: {po_proposal} — any ACs technically impossible or ambiguous?
- Engineer approach: {eng_approach} — aligned with Clean Architecture?
- QA scenarios: {qa_scenarios} — any that reveal architecture concerns?

Tasks:
1. Challenge PO: flag ACs that are technically unclear
2. Validate/challenge Engineer: correct patterns? realistic effort?
3. Discover new risks from QA scenarios
4. Update estimates with full picture
5. Final architecture recommendation
6. Security/deployment verdict from QA feedback

Output: Challenges + revised estimates + architecture decisions
```

#### Engineer Agent (with all Round 1)

```text
You are the Engineer. You proposed: {eng_approach}
Now challenge:
- PO stories: {po_proposal} — simple-sounding ACs that are actually complex?
- Tech Lead estimates: {tl_assessment} — agree with SP? add evidence
- QA edge cases: {qa_scenarios} — any that change implementation approach?

Tasks:
1. Challenge PO: "AC3 sounds simple but needs X because..."
2. Agree/disagree with Tech Lead estimates — cite codebase evidence
3. Adjust approach for QA's edge cases
4. Push back on unrealistic expectations
5. Final effort breakdown

Output: Challenges + revised effort + scope pushback with evidence
```

#### QA Agent (with all Round 1)

```text
You are QA. You found: {qa_scenarios}
Now review with full context:
- PO revised nothing yet: {po_proposal} — ACs still vague?
- Tech Lead risks: {tl_assessment} — new test scenarios from risks?
- Engineer gotchas: {eng_approach} — new edge cases from implementation?

Tasks:
1. New edge cases from Tech Lead's risk areas
2. New scenarios from Engineer's gotchas
3. Final testability verdict per AC (pass/fail/needs revision)
4. Acceptance test plan outline
5. "What about..." — final round of challenges
6. Security test priorities (top 3 risks)
7. Accessibility checklist for FE stories (if applicable)

Output: Final testability verdicts + new scenarios + test plan outline
```

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
