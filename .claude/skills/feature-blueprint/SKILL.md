---
name: feature-blueprint
disable-model-invocation: true
context: fork
compatibility: [jira-cache-server, mcp-atlassian]
description: |
  Multi-perspective feature blueprint on Confluence — 5 roles debate (PO, Domain Expert, Tech Lead, Engineer, QA).
  Outputs: structured Confluence page + backlog map for downstream /create-epic + /story-full.
  Supports 3 tiers: S (quick, no debate) / M (standard, 2 rounds) / L (full + page tree).
  Use when: new feature needing architecture review, multi-service changes, greenfield features before Jira.
  Triggers: "feature blueprint", "architecture doc", "design doc", "blueprint", "feature spec",
  "multi-perspective design", "research feature", "ทำ blueprint"
argument-hint: "[feature-description or {{PROJECT_KEY}}-XXX or Confluence-page-ID]"
---

# /feature-blueprint

**Mode:** Multi-Perspective Research + Debate (5 roles, 2 rounds)
**Output:** Confluence page (8 sections) + `blueprint_backlog_map` for downstream skills

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`
- **Stack:** AdonisJS 5.9 + Effect-TS + Clean Architecture (API) · Next.js 14 + Chakra UI (Website) · Next.js 14 + Tailwind + Headless UI (Admin)

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Gather | `feature_brief`, `existing_context{}`, `related_issues[]`, `confluence_refs[]` |
| 2. Size | `tier` (S/M/L), `sections_to_generate[]`, `skip_debate` (bool) |
| 3. Explore | `codebase_context{}` (file_paths[], patterns[], dependencies[]) |
| 4. Round 1 | `po_proposal`, `domain_analysis`, `tl_architecture`, `eng_spec`, `qa_risks_tests` |
| 5. Round 2 | `po_revised`, `domain_revised`, `tl_verdict`, `eng_verdict`, `qa_verdict` |
| 6. Converge | `blueprint_sections{}` (S1-S8), `debate_summary[]`, `consensus_checks{}` |
| 7. QG | `qg_score`, `qg_passed`, `qg_fixes[]` |
| 8. Confluence | `page_id` (or `page_ids[]` for L-tier), `page_url` |
| 9. Bridge | `blueprint_backlog_map{}` (stories[], spikes[], dependencies[], non_goals[]) |
| 10. Handoff | `next_skills[]`, `summary` |

> **Workflow Patterns:** See [workflow-patterns.md](../shared-references/workflow-patterns.md) for Gate Levels, ITERATE cycle, Parallel Explore.

## Document Structure (8 Sections)

| # | Section | Owner | Audience | Non-tech reads? |
|---|---------|-------|----------|----------------|
| S1 | Executive Summary | Main (synthesized) | Everyone | Yes |
| S2 | Business Case & User Scenarios | PO | Stakeholders | Yes |
| S3 | Domain Analysis | Domain Expert | TL/Engineers | Yes (tables) |
| S4 | Architecture & Design | Tech Lead | Engineers | No |
| S5 | Technical Specification | Engineer | Engineers | No |
| S6 | Risks, Edge Cases & Rabbit Holes | QA + Engineer | Everyone | Yes (risk table) |
| S7 | Test Strategy | QA | QA/Engineers | No |
| S8 | Delivery Plan | PO + Tech Lead | Everyone | Yes |

**Progressive disclosure:** Non-tech stakeholders read S1-S3, S6 risk table, S8. Engineers read all.

**Non-negotiable:**

- S4 **must have "Alternatives Considered"** with ≥2 options + pros/cons + rationale
- S1-S2 come before S4-S5 (user/customer first, then technical)
- All sections follow Thai + transliteration per [writing-style.md](../shared-references/writing-style.md)

## Size Tiers

| Tier | Criteria | Sections | Debate? | Confluence |
|------|----------|----------|---------|------------|
| **S** (Quick) | 1 service, 1-2 stories, clear scope | S1,S2,S4,S6,S8 | No (single-pass) | Single page |
| **M** (Standard) | Multi-service, 3-5 stories | All S1-S8 | Yes (2 rounds) | Single page + ToC |
| **L** (Full) | System-level, 6+ stories, new domain | All S1-S8 | Yes (2 rounds) | Parent + 8 child pages |

---

## Phases

> **Phase Tracking:** Use TodoWrite to mark each phase `in_progress` → `completed`.

### 1. Gather Context

**Input types:**

| Input | Action |
|-------|--------|
| Feature text | Capture as-is into `feature_brief` |
| Jira key ({{PROJECT_KEY}}-XXX) | `cache_get_issue` → read narrative, ACs, epic context |
| Confluence page ID | `confluence_get_page` → read existing doc structure |
| Epic key | Read overview + existing children via `cache_search` |

**Actions:**

1. Read input + parent epic/page (if exists)
2. Dedup check: `cache_search` or `cache_similar_issues` for related blueprints/stories
3. Summarize into `feature_brief`: what we know, what we don't, affected services

**⛔ GATE** — Present understanding + affected services to user. Ask:

- Is this the right scope?
- Any constraints or prior decisions I should know?
- Any existing docs/research to incorporate?

Proceeding without confirmation risks exploring the wrong scope and wasting agent tokens. Wait for explicit user approval.

### 2. Size & Scope Decision

Based on `feature_brief`, determine:

1. **Tier:** S / M / L (auto-suggest, user confirms)
2. **Sections to generate:** S-tier = S1,S2,S4,S6,S8 only; M/L = all S1-S8
3. **Debate strategy:** S-tier skips Phases 4-5 (single-pass generation); M/L runs full debate

| Signal | Suggests Tier |
|--------|--------------|
| Single service, well-understood domain | S |
| Multi-service, 3-5 stories estimated | M |
| New domain, system-level, 6+ stories | L |
| User explicitly says "quick" or "lightweight" | S |
| User explicitly says "thorough" or "full analysis" | L |

**⛔ GATE** — Confirm tier + section list with user. "This looks like a [M] feature. I'll generate [all 8 / 5] sections [with / without] multi-role debate. Approve?"

### 3. Codebase Exploration

> Skip for S-tier if user provides sufficient context or feature is purely conceptual.

Launch 2-3 `Task(Explore)` agents **IN PARALLEL** per [Parallel Explore](../shared-references/workflow-patterns.md):

| Agent | Focus |
|-------|-------|
| Backend | Models, services, routes, middleware, Effect-TS patterns relevant to feature |
| Frontend | Pages, components, hooks, state management relevant to feature |
| Shared/Infra | Config, types, env vars, cross-service patterns (if multi-service) |

**Validation:** Glob-validate all file paths. Generic paths REJECTED. Re-explore max 2 attempts.

**🟢 AUTO** — Merge results into `codebase_context`. Proceed to debate.

### 4. Round 1: Propose (5 Parallel Agents)

> S-tier: SKIP this phase. Main session generates sections in a single pass instead.

Launch 5 agents **IN PARALLEL** (single message, 5 Task calls). Each proposes independently without seeing others.

**Agent prompts:** See [references/agent-prompts.md](references/agent-prompts.md) — **Round 1** section. Substitute all `{...}` placeholders with full text before launching.

| Agent | Model | Sections | Word Limit |
|-------|-------|----------|------------|
| PO | sonnet | S2 + S8 partial | 800 |
| Domain Expert | sonnet | S3 | 500 |
| Tech Lead | opus | S4 + S8 partial | 1000 |
| Engineer | sonnet | S5 | 800 |
| QA | sonnet | S6 + S7 | 600 |

**🟢 AUTO** — Collect all 5 results. Proceed to Round 2.

### 5. Round 2: Challenge (5 Parallel Agents)

> S-tier: SKIP this phase.

Share **ALL Round 1 outputs** to each agent. Launch 5 agents **IN PARALLEL**.

**Agent prompts:** See [references/agent-prompts.md](references/agent-prompts.md) — **Round 2** section. Each agent challenges the others based on their expertise.

| Agent | Focus | Word Limit |
|-------|-------|------------|
| PO | Accept/reject architecture per user value, revise appetite | 600 |
| Domain Expert | Validate bounded contexts vs scenarios + data model | 400 |
| Tech Lead | Challenge estimates, validate patterns, security/deployment verdict | 800 |
| Engineer | Flag deceptive complexity, revise effort with evidence | 600 |
| QA | New edge cases from all inputs, security tests, accessibility verdict | 500 |

**🟢 AUTO** — Collect all 5 results. Proceed to convergence.

### 6. Converge

**Main session synthesizes** all agent outputs (Round 1 + Round 2 for M/L; single-pass for S):

#### 6a. Blueprint Sections

| Section | Source |
|---------|--------|
| S1 — Executive Summary | Synthesized: PO business case + TL architecture decision (1 paragraph) |
| S2 — Business Case & User Scenarios | PO Round 2 (revised after debate) |
| S3 — Domain Analysis | Domain Expert Round 2 (refined after challenges) |
| S4 — Architecture & Design | TL Round 2 + alternatives table (MUST have ≥2 options) |
| S5 — Technical Specification | Engineer Round 2 + codebase paths |
| S6 — Risks, Edge Cases & Rabbit Holes | QA + Engineer combined, deduplicated |
| S7 — Test Strategy | QA Round 2 |
| S8 — Delivery Plan | PO + TL consensus: VS plan, story breakdown, sprint mapping, team assignment |

#### 6b. Debate Summary Table

Show only **disagreements and their resolutions** — skip topics where all agreed.

| Topic | PO | Domain | TL | Engineer | QA | Resolution |
|-------|----|--------|----|----------|----|-----------|
| [item] | [position] | [position] | [position] | [position] | [position] | [decision] |

#### 6c. Consensus Checks

- [ ] All roles agree on MVP scope?
- [ ] Estimate variance < 2x between Tech Lead and Engineer?
- [ ] All critical QA edge cases addressed or explicitly excluded?
- [ ] Alternatives Considered has ≥2 options with rationale?
- [ ] No unresolved open questions marked "blocker"?
- [ ] VS plan validated by Tech Lead and Engineer?

If any check fails → flag to user with the disagreement.

**🔄 ITERATE** — Present blueprint as numbered section cards. Ask:

- **Approve** → proceed to QG
- **Annotate** → user specifies section # and notes → revise ONLY affected sections by re-running relevant role agents (e.g., S4 change → re-run TL + Engineer only, max 3 rounds)
- **Major rework** → back to Phase 1

### 7. Quality Gate — Blueprint

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: Writing to Confluence before QG ≥ 90% risks publishing incomplete/inconsistent documents. Auto-fix first, escalate if still failing.

Score against `shared-references/verification-checklist.md` — Blueprint Quality (B1-B8):

| # | Check | Criteria |
|---|-------|----------|
| B1 | Executive Summary | 1 paragraph, mentions problem + solution + who benefits |
| B2 | Business Case | Problem narrative, ≥2 user scenarios, non-goals listed, appetite defined |
| B3 | Domain Analysis | ≥1 bounded context, ≥1 domain event, entities with attributes |
| B4 | Architecture | **Alternatives ≥2 options** with pros/cons, chosen approach with rationale |
| B5 | Technical Spec | Real file paths (Glob-validated), endpoints with HTTP methods + status codes |
| B6 | Risks | ≥3 risks with severity + mitigation, ≥2 edge cases, open questions listed |
| B7 | Test Strategy | Test approach per affected layer, ≥3 critical test scenarios |
| B8 | Delivery Plan | VS plan exists, stories mapped to VS labels, sprint estimate, dependency order |

**Scoring:**

- S-tier (5 sections): `Blueprint Quality X/5 | Overall X%` (B1+B2+B4+B6+B8)
- M/L-tier (8 sections): `Blueprint Quality X/8 | Overall X%` (B1-B8)

**Auto-fix paths:**

- B1-B4, B6-B8: auto-fix from debate context → re-check
- B5 fail (generic paths): launch targeted `Task(Explore)` on the service with generic paths → Glob-validate → re-score

Max 2 auto-fix attempts. Escalate if still failing.

### 8. Write to Confluence

> **🟢 AUTO** — If Phase 7 QG passed → write automatically.

**Page structure by tier:**

| Tier | Structure |
|------|-----------|
| S | Single page under feature parent |
| M | Single page with `{toc:maxLevel=2}` macro |
| L | Parent page + 8 child pages (one per section) |

**Page title:** `[Blueprint] {Feature Name}`

**Confluence section format** (follows [writing-style.md](../shared-references/writing-style.md) numbered section pattern):

```text
{toc:maxLevel=2}

1. 📋 Executive Summary        (info panel)
2. 💼 Business Case & User Scenarios  (info panel + scenario table)
3. 🏗️ Domain Analysis           (tables: contexts, events, aggregates)
4. 🔧 Architecture & Design    (info panel + alternatives table)
5. ⚙️ Technical Specification   (tables: endpoints, data contracts, file paths)
6. ⚠️ Risks, Edge Cases & Rabbit Holes  (warning panel + risk register)
7. 🧪 Test Strategy             (success panel + test scenario table)
8. 📦 Delivery Plan             (VS table + story breakdown + sprint map)

---
📊 Debate Summary (note panel — disagreements only)
🔗 References (links to Jira epic, related pages)
```

**Creation flow:**

1. `confluence_create_page` (MCP) for page creation
2. For pages with macros (ToC, code blocks): use `update_page_storage.py`
3. For L-tier: create parent first, then children
4. Link to Jira epic if exists: `jira_create_remote_issue_link`

**🟢 AUTO** — After Confluence write, no cache invalidation needed (Confluence not cached).

### 9. Bridge to Backlog

**🟡 REVIEW** — Present conversion plan to user. Proceed unless user objects.

Generate `blueprint_backlog_map` from blueprint sections:

```json
{
  "blueprint_page_id": "CONF-XXX",
  "blueprint_url": "https://...",
  "epic": {
    "title": "[Feature Name]",
    "source_sections": ["S2", "S8"]
  },
  "stories": [
    {
      "title": "[TAG] - Description (English Name)",
      "narrative_hint": "From S2 scenario N",
      "acs_hint": ["From S2 scenario + S6 edge cases"],
      "vs_label": "vs2-...",
      "sp_estimate": "M",
      "priority": "MVP"
    }
  ],
  "spikes": [
    {
      "title": "[Spike] - Open question from S6",
      "timebox": "4h",
      "source": "S6 open questions"
    }
  ],
  "dependencies": [
    { "from": "Story 1", "to": "Story 2", "type": "blocks" }
  ],
  "non_goals": ["Item from S2 non-goals"]
}
```

**Conversion mapping:**

| Blueprint Section | Jira Artifact | Downstream Skill |
|---|---|---|
| Whole doc | Epic | `/create-epic` |
| User Scenarios (S2) | User Stories | `/story-full` |
| Risk mitigations (S6) | Spike stories | `/create-task type=spike` |
| Open Questions (S6) | Spike stories | `/create-task type=spike` |
| Test Strategy (S7) | QA Sub-tasks | `/create-testplan` |
| Non-Goals (S2) | Epic exclusions | Merged into epic desc |
| Dependencies (S8) | Issue Links | `jira_create_issue_link` |

> **Note:** Blueprint does NOT auto-create Jira issues. User triggers downstream skills manually with context from `blueprint_backlog_map`.

### 10. Handoff

```text
## Blueprint Complete: [Feature Name]
Confluence: [page URL]
Tier: [S/M/L] — [N] sections generated
Stories identified: X (Y MVP, Z deferred)
Spikes: N open questions → spike stories
Key risks: [top 2-3]

Next steps (pick creation order):
→ /create-epic [epic-title]     — create epic from blueprint
→ /story-full [first-story]     — create first MVP story + subtasks
→ /create-task type=spike       — create spike for open questions
→ /search-issues [keywords]     — dedup check before creating
```

Present each story as a numbered card for user to pick creation order.

---

## When to Use vs Skip

| Situation | Use `/feature-blueprint`? | Alternative |
|-----------|--------------------------|-------------|
| New feature, unclear scope, greenfield | **Yes** | — |
| Multi-service feature needing architecture review | **Yes** | — |
| Need cross-role alignment before sprint planning | **Yes** | — |
| Feature already has clear stories, needs refinement | **No** | `/refine-feature` |
| Simple bug fix / UI tweak | **No** | `/create-task` or `/story-full` |
| Requirements already detailed, ready to create | **No** | `/story-full` directly |
| Single-service, obvious approach | **No** | `/story-full` directly |

### `/feature-blueprint` vs `/refine-feature`

| | `/feature-blueprint` | `/refine-feature` |
|---|---|---|
| **When** | Before any Jira artifacts (greenfield) | Refining existing/draft stories |
| **Input** | Feature idea / concept | Jira key / draft stories |
| **Output** | Confluence doc + backlog map | Refined stories → `/story-full` |
| **Roles** | 5 (+ Domain Expert) | 4 (no Domain Expert) |
| **Scope** | Architecture-level (Epic-sized) | Story-level |
| **Downstream** | → `/create-epic` → `/story-full` | → `/story-full` |

**Token budget:** S ~40K, M ~80K, L ~120K. Justified by reduced rework + cross-role alignment before implementation.

---

## S-tier Shortcut

For small features (S-tier), skip Phases 4-5 entirely. Main session generates sections in a **single pass**:

1. Write S1 (Executive Summary) — 1 paragraph
2. Write S2 (Business Case) — scenarios + non-goals
3. Write S4 (Architecture) — approach + alternatives (still mandatory)
4. Write S6 (Risks) — edge cases + risk register
5. Write S8 (Delivery Plan) — stories + sprint mapping

No subagents launched. ~40K tokens total.

---

## Example

**Input:** "ระบบ notification แบบ real-time สำหรับ platform (push notification + in-app)"

**Phase 2 output:** Tier M — multi-service (BE + Website + Admin), ~4 stories estimated

**Round 1 highlights:**

| Role | Key Points |
|------|-----------|
| PO | 4 scenarios: receive push, view in-app list, mark read, notification preferences. Appetite: 2 sprints. Non-goal: email notifications |
| Domain Expert | 2 bounded contexts: Notification (new) + User Preference (existing). Events: `NotificationSent`, `NotificationRead`, `PreferenceUpdated` |
| Tech Lead | New `NotificationService` Effect service + WebSocket for real-time. Alternative: polling vs WebSocket vs SSE → chose WebSocket. L estimate (5 SP) per story |
| Engineer | Reuse `FCMService` pattern from existing push. 20h total. Gotcha: WebSocket connection management on Next.js |
| QA | "What if user has 1000 unread?" + "notification arrives while user is on notification page?" + "push permission denied?" |

**Round 2 highlights:**

| Debate | Resolution |
|--------|-----------|
| PO wanted notification preferences in MVP | **Kept** — QA flagged edge cases, Engineer confirmed 4h extra is worth it |
| TL chose WebSocket over SSE | **Challenged by Engineer** — SSE simpler for one-way push → **Revised to SSE** for MVP, WebSocket deferred |
| QA's "1000 unread" edge case | **Added pagination** — Engineer confirmed, TL agreed on virtual scroll |
| Domain Expert flagged missing `NotificationBatch` aggregate | **Added** — TL confirmed batch send needed for class reminders |

**Output:** Confluence page with 8 sections + backlog map with 4 stories + 1 spike

---

## References

- [Writing Style](../shared-references/writing-style.md) — Thai + transliteration, concise, scan-first
- [Workflow Patterns](../shared-references/workflow-patterns.md) — Gate levels, ITERATE cycle, Parallel Explore
- [Vertical Slice Guide](../shared-references/vertical-slice-guide.md) — VS patterns, labels
- [Verification Checklist](../shared-references/verification-checklist.md) — Quality criteria (B1-B8 for blueprints)
- [Tools](../shared-references/tools.md) — Confluence tool selection
- After blueprint: `/create-epic` → `/story-full` → `/create-testplan`
