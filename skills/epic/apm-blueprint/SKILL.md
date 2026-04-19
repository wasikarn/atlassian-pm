---
name: apm-blueprint
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian]
description: |
  Multi-perspective feature blueprint on Confluence — 3 roles debate (PO, Tech Lead, QA).
  Outputs: structured Confluence page + backlog map for downstream /create-epic + /create-task.
  Supports 3 tiers: S (quick, no debate) / M (standard, single round) / L (full + page tree).
  Triggers: "feature blueprint", "architecture doc", "design doc", "blueprint", "feature spec",
  "multi-perspective design", "research feature", "ทำ blueprint"
  Use when: new feature needing architecture review, multi-service changes, greenfield features before Jira.
  Do NOT use for: creating a task without architecture review (use create-task); updating an existing epic (use update-epic).
argument-hint: "[feature-description or ABC-XXX or Confluence-page-ID]"
effort: high
---

# /atlassian-pm:apm-blueprint

**Mode:** Multi-Perspective Research + Debate (3 roles, 1 round)
**Output:** Confluence page (8 sections) + `blueprint_backlog_map` for downstream skills

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Gather | `feature_brief`, `existing_context{}`, `related_issues[]`, `confluence_refs[]` |
| 2. Size | `tier` (S/M/L), `sections_to_generate[]`, `skip_debate` (bool) |
| 3. Explore | `codebase_context{}` (file_paths[], patterns[], dependencies[]) |
| 4. Debate | `po_proposal`, `tl_architecture`, `qa_risks_tests` |
| 5. Converge | `blueprint_sections{}` (S1-S8), `debate_summary[]`, `consensus_checks{}` |
| 6. QG | `qg_score`, `qg_passed`, `qg_fixes[]` |
| 7. Confluence | `page_id` (or `page_ids[]` for L-tier), `page_url` |
| 8. Bridge | `blueprint_backlog_map{}` (tasks[], spikes[], dependencies[], non_goals[]) |
| 9. Handoff | `next_skills[]`, `summary` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels, ITERATE cycle, Parallel Explore.

## Document Structure (8 Sections)

S1 Executive Summary (Main) · S2 Business Case & User Scenarios (PO) · S3 Domain Analysis (TL) · S4 Architecture & Design (TL) · S5 Technical Specification (Engineer) · S6 Risks & Edge Cases (QA+Engineer) · S7 Test Strategy (QA) · S8 Delivery Plan (PO+TL)

Non-tech: read S1-S3, S6 risk table, S8. Engineers: read all.

**Non-negotiable:**

- S4 **must have "Alternatives Considered"** with ≥2 options + pros/cons + rationale; M/L tier **must include "Performance & Scale Assumptions"** (target QPS, latency budget, data volume projection)
- S1-S2 come before S4-S5 (user/customer first, then technical)
- All sections follow Thai + transliteration per [writing-style.md](../../../references/writing-style.md)

## Size Tiers

| Tier | Criteria | Sections | Debate? | Confluence |
|------|----------|----------|---------|------------|
| **S** (Quick) | 1 service, 1-2 tasks, clear scope | S1,S2,S4,S6,S8 | No (single-pass) | Single page |
| **M** (Standard) | Multi-service, 3-5 tasks | All S1-S8 | Yes (1 round, 3 agents) | Single page + ToC |
| **L** (Full) | System-level, 6+ tasks, new domain | All S1-S8 | Yes (1 round, 3 agents) | Parent + 8 child pages |

## Phases

### 1. Gather Context

Build `feature_brief` from user input — understand scope, affected services, and what is already known.

| Input | Action |
|-------|--------|
| Feature text | Capture as-is into `feature_brief` |
| Jira key (ABC-XXX) | `cache_get_issue(key)` → read narrative, ACs, epic context |
| Confluence page ID | `confluence_get_page(id)` → read existing doc structure |
| Epic key | Read overview + existing children via `cache_search` |

> **🟢 PARALLEL** — `cache_get_issue` / `confluence_get_page` + `cache_similar_issues`. Summarize after both complete.

1. Read input + parent epic/page (if exists)
2. Dedup check: `cache_search` or `cache_similar_issues` for related blueprints/stories
3. Summarize into `feature_brief`: what we know, what we don't, affected services

**⛔ GATE** — Present understanding + affected services to user. Ask: Is scope correct? Any constraints or prior decisions? Any existing docs to incorporate? Wait for explicit approval.

### 2. Size & Scope Decision

Agree on tier (S/M/L), sections to generate, and debate strategy before any agent work.

| Signal | Suggests Tier |
|--------|--------------|
| Single service, well-understood domain | S |
| Multi-service, 3-5 tasks estimated | M |
| New domain, system-level, 6+ tasks | L |
| User says "quick" or "lightweight" | S |
| User says "thorough" or "full analysis" | L |

S-tier skips Phases 4-5 (single-pass generation). M/L runs full debate.

**⛔ GATE** — Confirm tier + section list. "This looks like a [M] feature. I'll generate [all 8 / 5] sections [with / without] multi-role debate. Approve?"

### 3. Codebase Exploration

Discover real file paths, patterns, and cross-service dependencies to ground the debate in actual code.

> Skip for S-tier if user provides sufficient context or feature is purely conceptual.

Launch **1** `Task(Explore)` agent on the most relevant service(s). Focus on models, services, routes, key patterns, and cross-service boundaries.

**Validation:** Glob-validate all file paths. Generic paths REJECTED. Re-explore max 2 attempts.

**🟢 AUTO** — Merge results into `codebase_context`. Proceed to debate.

### 4. Debate (3 Parallel Agents)

> S-tier: SKIP this phase. Main session generates sections in a single pass.

Launch 3 agents **IN PARALLEL** (single message, 3 Task calls). Each proposes independently without seeing others.

**Agent prompts:** See [references/agent-prompts.md](references/agent-prompts.md) — **Debate** section. Substitute all `{...}` placeholders before launching.

| Agent | Model | Sections | Word Limit | maxTurns |
| ------- | ------- | ---------- | ---------- | -------- |
| PO | sonnet | S2 + S8 partial | 800 | 8 |
| Tech Lead | sonnet | S3 + S4 + S5 + S8 partial | 1200 | 10 |
| QA | sonnet | S6 + S7 | 600 | 8 |

> **maxTurns enforcement:** Set `maxTurns` per table. Uncapped agents on complex features can consume 30+ turns.

**🟢 AUTO** — Collect all 3 results. Proceed to convergence.

### 5. Converge

Synthesize agent outputs into final 8-section blueprint, resolve disagreements, get user approval.

#### 5a. Blueprint Sections

S1: synthesized PO+TL (1 paragraph) · S2: PO proposal · S3: TL domain entities/bounded contexts · S4: TL architecture + alternatives table (≥2 options, required) + Performance & Scale Assumptions (M/L tier) · S5: TL implementation spec/endpoints/data model · S6: QA+TL risks combined, deduplicated · S7: QA test strategy · S8: PO+TL consensus VS plan + story breakdown + team assignment

#### 5b. Debate Summary

Show only disagreements + resolutions (skip agreed topics). Table: Topic | PO | TL | QA | Resolution.

#### 5c. Consensus Checks

- [ ] PO and TL agree on MVP scope?
- [ ] All critical QA edge cases addressed or explicitly excluded?
- [ ] Alternatives Considered has ≥2 options with rationale?
- [ ] No unresolved open questions marked "blocker"?
- [ ] VS plan validated by Tech Lead?

If any check fails → flag to user with the disagreement.

**🔄 ITERATE** — Present blueprint as numbered section cards. Ask:

- **Approve** → proceed to QG
- **Annotate** → user specifies section # and notes → revise ONLY affected sections (max 3 rounds)
- **Major rework** → back to Phase 1

### 6. Quality Gate — Blueprint

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> **HR1:** NEVER write to Confluence before QG ≥ 90%.

Score against `verification-checklist.md` — Blueprint Quality (B1-B8). Target: ≥ 90%.

- S-tier (5 sections): `Blueprint Quality X/5 | Overall X%` (B1+B2+B4+B6+B8)
- M/L-tier (8 sections): `Blueprint Quality X/8 | Overall X%` (B1-B8)

**Auto-fix paths:**

- B1-B4, B6-B8: auto-fix from debate context → re-check
- B5 fail (generic paths): launch targeted `Task(Explore)` → Glob-validate → re-score

Max 2 auto-fix attempts. Escalate if still failing.

### 7. Write to Confluence

> **🟢 AUTO** — If Phase 6 QG passed → write automatically.
> **HR4:** Use `update_page_storage.py` for pages with macros (ToC, code blocks).

| Tier | Structure |
|------|-----------|
| S | Single page under feature parent |
| M | Single page with `{toc:maxLevel=2}` macro |
| L | Parent page + 8 child pages (one per section) |

**Page title:** `[Blueprint] {Feature Name}`

**Confluence section format:** `{toc:maxLevel=2}` · S1 info panel · S2 info+scenario table · S3 domain tables · S4 info+alternatives table · S5 endpoints/data tables · S6 warning panel+risk register · S7 success panel+test table · S8 VS table+sprint map · Debate Summary (note panel) · References

**Creation flow:**

1. `confluence_create_page` (MCP) for page creation
2. For pages with macros: `update_page_storage.py`
3. L-tier: create parent first, then children
4. Link to Jira epic if exists: `jira_create_remote_issue_link`

### 8. Bridge to Backlog

Convert published blueprint into `blueprint_backlog_map` for downstream skills.

**🟡 REVIEW** — Present conversion plan to user. Proceed unless user objects.

→ ADF format: see ../../../references/templates-core.md

`blueprint_backlog_map` fields: `blueprint_page_id`, `blueprint_url`, `epic{title, source_sections}`, `tasks[]{title, objective_hint, acs_hint[], vs_label, sp_estimate, priority}`, `spikes[]{title, timebox, source}`, `dependencies[]{from, to, type}`, `non_goals[]`

**Conversion:** whole doc → Epic (`/create-epic`) · S2 scenarios → Tasks (`/create-task`) · S6 risks/questions → Spikes (`/create-task type=spike`) · S7 → QA Tasks (`/create-testplan`) · S2 non-goals → epic exclusions · S8 dependencies → `jira_create_issue_link`

> Blueprint does NOT auto-create Jira issues. User triggers downstream skills manually.

### 9. Handoff

Output: `Blueprint Complete: [Feature Name]` · Confluence URL · tier + section count · stories (MVP/deferred) · spikes · top risks · numbered story cards for creation order.

Next steps: `/create-epic` → `/create-task` → `/create-task type=spike` → `/search-issues`

> When to use vs alternatives: [references/decision-guide.md](references/decision-guide.md) · S-tier single-pass: [references/s-tier-shortcut.md](references/s-tier-shortcut.md)

## Examples

```text
/blueprint "Real-time video analytics dashboard"       # good: feature description
/blueprint {{PROJECT_KEY}}-48                          # good: epic key → reads existing scope
/blueprint "Multi-tenant permission system" --tier L   # good: new domain, explicit tier L
/blueprint 12345678                                    # good: Confluence page ID as input

/blueprint "add button to export CSV"    # bad: single-task scope → use /create-task
/blueprint                               # bad: no input → all roles produce generic output
/blueprint "improve UX" --tier M         # bad: vague description, Phase 1 gate will block
```

**Common mistakes:**

- Not feeding `blueprint_backlog_map` to `/create-epic` — manually recreating stories skips VS mapping
- Skipping Phase 1 scope gate — wrong scope wastes all agent tokens
- Requesting tier L for 2-3 story features — S or M unless genuinely system-level
- Not linking blueprint page to Epic after creation — `/create-epic` picks up `blueprint_page_id` from session history; new session loses handoff

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[Writing Style](../../../references/writing-style.md) · [Workflow Patterns](../../../references/workflow-patterns.md) · [Vertical Slice Guide](../../../references/vertical-slice-guide.md) · [Verification Checklist](../../../references/verification-checklist.md) · [Tools](../../../references/tools.md) · [Decision Guide](references/decision-guide.md) · [S-tier Shortcut](references/s-tier-shortcut.md) · [Examples](references/examples.md)

After blueprint: `/create-epic` → `/create-task` → `/create-testplan`
