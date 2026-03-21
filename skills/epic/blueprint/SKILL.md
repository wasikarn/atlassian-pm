---
name: blueprint
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache-server, mcp-atlassian]
description: |
  Multi-perspective feature blueprint on Confluence — 5 roles debate (PO, Domain Expert, Tech Lead, Engineer, QA).
  Outputs: structured Confluence page + backlog map for downstream /create-epic + /create-story.
  Supports 3 tiers: S (quick, no debate) / M (standard, 2 rounds) / L (full + page tree).
  Use when: new feature needing architecture review, multi-service changes, greenfield features before Jira.
  Triggers: "feature blueprint", "architecture doc", "design doc", "blueprint", "feature spec",
  "multi-perspective design", "research feature", "ทำ blueprint"
argument-hint: "[feature-description or ABC-XXX or Confluence-page-ID]"
---

# /blueprint

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

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels, ITERATE cycle, Parallel Explore.

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
- All sections follow Thai + transliteration per [writing-style.md](../../../references/writing-style.md)

## Size Tiers

| Tier | Criteria | Sections | Debate? | Confluence |
|------|----------|----------|---------|------------|
| **S** (Quick) | 1 service, 1-2 stories, clear scope | S1,S2,S4,S6,S8 | No (single-pass) | Single page |
| **M** (Standard) | Multi-service, 3-5 stories | All S1-S8 | Yes (2 rounds) | Single page + ToC |
| **L** (Full) | System-level, 6+ stories, new domain | All S1-S8 | Yes (2 rounds) | Parent + 8 child pages |

## Phases

### 1. Gather Context

**Input types:**

| Input | Action |
|-------|--------|
| Feature text | Capture as-is into `feature_brief` |
| Jira key (ABC-XXX) | `cache_get_issue` → read narrative, ACs, epic context |
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

Launch 2-3 `Task(Explore)` agents **IN PARALLEL** per [Parallel Explore](../../../references/workflow-patterns.md):

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

| Agent | Model | Sections | Word Limit | maxTurns |
| ------- | ------- | ---------- | ---------- | -------- |
| PO | sonnet | S2 + S8 partial | 800 | 8 |
| Domain Expert | sonnet | S3 | 500 | 8 |
| Tech Lead | opus | S4 + S8 partial | 1000 | 10 |
| Engineer | sonnet | S5 | 800 | 8 |
| QA | sonnet | S6 + S7 | 600 | 8 |

> **maxTurns enforcement:** Set `maxTurns` per table when launching Task agents. Uncapped agents on complex features can consume 30+ turns; these caps prevent runaway costs.

**🟢 AUTO** — Collect all 5 results. Proceed to Round 2.

### 5. Round 2: Challenge (5 Parallel Agents)

> S-tier: SKIP this phase.

Share **ALL Round 1 outputs** to each agent. Launch 5 agents **IN PARALLEL**.

> **maxTurns enforcement:** Set `maxTurns` per table when launching Task agents.

**Agent prompts:** See [references/agent-prompts.md](references/agent-prompts.md) — **Round 2** section. Each agent challenges the others based on their expertise.

| Agent | Focus | Word Limit | maxTurns |
| ------- | ------- | ---------- | -------- |
| PO | Accept/reject architecture per user value, revise appetite | 600 | 8 |
| Domain Expert | Validate bounded contexts vs scenarios + data model | 400 | 8 |
| Tech Lead | Challenge estimates, validate patterns, security/deployment verdict | 800 | 10 |
| Engineer | Flag deceptive complexity, revise effort with evidence | 600 | 8 |
| QA | New edge cases from all inputs, security tests, accessibility verdict | 500 | 8 |

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

Score against `shared-references/verification-checklist.md` — Blueprint Quality (B1-B8).
Load the file to see full criteria before scoring. Target: ≥ 90%.

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

**Confluence section format** (follows [writing-style.md](../../../references/writing-style.md) numbered section pattern):

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
| User Scenarios (S2) | User Stories | `/create-story` |
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
→ /create-story [first-story]   — create first MVP story + subtasks
→ /create-task type=spike       — create spike for open questions
→ /search-issues [keywords]     — dedup check before creating
```

Present each story as a numbered card for user to pick creation order.

## When to Use vs Skip

> See [references/decision-guide.md](references/decision-guide.md) for when to use this skill vs alternatives and comparison with /refine-epic.

## S-tier Shortcut

> See [references/s-tier-shortcut.md](references/s-tier-shortcut.md) for S-tier single-pass generation steps.

## Examples

### ✅ Good

```text
/blueprint "Real-time video analytics dashboard"          # feature description seeds all 5 roles with focused context
/blueprint {{PROJECT_KEY}}-48                                         # epic key → reads existing scope + children before debating
/blueprint "Multi-tenant permission system" --tier L      # explicitly request full tier for new domain / system-level work
/blueprint 12345678                                       # Confluence page ID → reads existing spec doc as input
```

### ❌ Bad

```text
/blueprint "add button to export CSV"                     # single-story scope → use /create-story directly, blueprint is overkill
/blueprint                                                # no input → debate has no grounding, all 5 roles produce generic output
/blueprint {{PROJECT_KEY}}-50                                         # running after Jira stories already exist defeats the purpose — blueprint informs Jira creation, not the reverse
/blueprint "improve UX" --tier M                          # vague description forces PO + TL to guess scope; Phase 1 gate will block anyway
```

**Common mistakes:**

- Using blueprint output without feeding it to `/create-epic` — the `blueprint_backlog_map` is the handoff artifact; manually recreating stories from the Confluence page skips structured VS mapping.
- Skipping the Phase 1 scope gate — confirming the wrong scope before debate means all 5 agents explore the wrong problem, wasting significant tokens.
- Requesting tier L for features that are clearly 2-3 stories — L-tier spins up 10 parallel agents across 2 rounds; use S or M unless the feature is genuinely system-level.
- Not linking the blueprint Confluence page to the Epic after creation — `/create-epic` picks up `blueprint_page_id` from session history; starting a new session loses that handoff.

## Example

> See [references/examples.md](references/examples.md) for a full input/output example with Round 1 and Round 2 highlights.

## References

- [Writing Style](../../../references/writing-style.md) — Thai + transliteration, concise, scan-first
- [Workflow Patterns](../../../references/workflow-patterns.md) — Gate levels, ITERATE cycle, Parallel Explore
- [Vertical Slice Guide](../../../references/vertical-slice-guide.md) — VS patterns, labels
- [Verification Checklist](../../../references/verification-checklist.md) — Quality criteria (B1-B8 for blueprints)
- [Tools](../../../references/tools.md) — Confluence tool selection
- [Decision Guide](references/decision-guide.md)
- [S-tier Shortcut](references/s-tier-shortcut.md)
- [Examples](references/examples.md)
- After blueprint: `/create-epic` → `/create-story` → `/create-testplan`
