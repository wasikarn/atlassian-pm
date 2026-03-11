# Skill Orchestration

> Intent-to-skill mapping, quality gates, and decision trees.
> Read this before creating/editing Jira issues.

## Intent-to-Skill Map

| Intent | Skill Chain | Gate |
| --- | --- | --- |
| Feature blueprint | `/feature-blueprint` → `/create-epic` → `/story-full` → verify | ≥ 90% (Confluence) |
| Refine feature | `/search-issues` → `/refine-feature` → `/story-full` → verify | N/A (pre-creation) |
| Create epic | `/search-issues` → `/create-epic` → verify | ≥ 90% |
| Create story | `/search-issues` → `/story-full` → verify | ≥ 90% |
| Create task | `/search-issues` → `/create-task` → verify | ≥ 90% |
| Analyze story | `/analyze-story` → verify `--with-subtasks` | ≥ 90% |
| Test plan | `/create-testplan` → verify | ≥ 90% |
| Update single | `/update-{epic,story,task,subtask}` → verify | ≥ 90% |
| Update cascade | `/sync-alignment` → verify `--with-subtasks` | ≥ 90% |
| Plan sprint | `/plan-sprint` → `/dependency-chain` | N/A |

**Rules:**

- Always `/search-issues` before creating (dedup)
- Always `/verify-issue` after creating/editing
- Use `/story-full` for new stories (combines PO + TA). Use `/analyze-story` only for existing stories needing subtasks

## HARD RULES

> Rules that if violated cause **silent failures**, **data corruption**, or **irreversible damage**.
> Every skill MUST respect these rules. No exceptions.

### HR1. Quality Gate ≥ 90% Before Atlassian Writes

> **NEVER create or edit issues on Jira/Confluence before passing QG ≥ 90%.** No "create first, fix later".

```text
BEFORE sending to Atlassian:
1. Explore codebase (real file paths — no generic paths)
2. Generate ADF JSON (template-compliant, panels, Given/When/Then)
3. Self-check against shared-references/verification-checklist.md
4. Score: Technical X/5 | Quality X/6 | Overall X%
5. If < 90% → auto-fix → re-score (max 2 attempts)
6. If >= 90% → proceed to Atlassian
7. If still < 90% after 2 fixes → ask user
8. MCP create shell (summary + parent ONLY — no description)
9. acli edit --from-json (ADF description from step 2)
10. After Atlassian write → cache_invalidate(issue_key)
```

**Why:** MCP `jira_create_issue` writes wiki markup descriptions directly to Jira, bypassing QG.

### HR2. JQL `parent` — No ORDER BY

NEVER add `ORDER BY` to JQL with `parent =`, `parent in`, or `key in (...)` — parser error, zero results.

### HR3. MCP Assignee — Use acli Only

`jira_update_issue` with assignee silently succeeds but does nothing. Use `acli jira workitem assign`.

### HR4. Confluence Macros — Use Script Only

MCP HTML-escapes `<ac:structured-macro>` → broken rendering. Use `update_page_storage.py`.

### HR5. Subtask = Two-Step + Verify Parent

MCP may silently ignore parent field → orphan subtask. Always: (1) MCP create with parent, (2) verify parent set via `jira_get_issue`, (3) acli edit for ADF.

### HR6. Cache Invalidate After Every Write

After any MCP write → `cache_invalidate(issue_key)`. Stale data causes wrong verify/cascade/planning results.

### HR7. Sprint ID — Always Lookup, Never Hardcode

Use `jira_get_sprints_from_board()` — hardcoded IDs cause tickets to land in wrong sprint silently.

### HR8. Subtask Size + Dates Must Align with Parent

Subtask dates within parent date range. Points sum reasonable vs parent estimate. Misalignment breaks capacity/burndown.

### HR9. Related Ticket Descriptions Must Align

Story ACs covered by subtask objectives. Epic scope reflected in child Stories. Linked tickets reference each other. `/verify-issue --with-subtasks` checks alignment (A1-A6).

### Scoring Reference

| Score | Status | Action |
| --- | --- | --- |
| 90-100% | Pass | Send to Atlassian |
| 70-89% | Warning | Auto-fix, then re-score |
| < 70% | Fail | Must fix, ask user if stuck |

### What Gets Scored

| Check | Max | Applies To |
| --- | --- | --- |
| T1-T5 Technical | 5 | All types |
| S1-S5 Story Quality | 6 | Story |
| ST1-ST5 Subtask Quality | 5 | Sub-task |
| QA1-QA5 QA Quality | 5 | QA Sub-task |
| B1-B8 Blueprint Quality | 8 (or 5 for S-tier) | Blueprint (Confluence) |
| E1-E4 Epic Quality | 4 | Epic |
| A1-A6 Alignment | 6 | `--with-subtasks` only |

Full checklist: `shared-references/verification-checklist.md`

## Decision Trees

### Create or Update?

```text
New requirement?
├─ Yes → /search-issues (dedup)
│        ├─ Duplicate found → /update-* or /sync-alignment
│        └─ No duplicate
│             ├─ Greenfield / architecture needed / new domain → /feature-blueprint → /create-epic → /story-full
│             ├─ Unclear scope / multi-service / high-risk → /refine-feature → /story-full
│             └─ Clear scope / single-service → /story-full (preferred)
└─ No → Edit existing
         ├─ Single issue → /update-{type}
         └─ Story + subtasks (± Confluence) → /sync-alignment
```

### story-full vs analyze-story?

```text
/story-full (default)
├─ Combined PO+TA = less context switching
├─ Use when: new story from scratch
└─ Output: Story + Sub-tasks in one go

/analyze-story (existing story only)
├─ Use when: story already exists in Jira, only need subtasks
└─ Skips story creation, starts from impact analysis
```

## Pre/Post Conditions

| Skill | Pre-condition | Post-condition |
| --- | --- | --- |
| `/feature-blueprint` | Feature idea / concept | Confluence page + backlog map → `/create-epic` → `/story-full` |
| `/refine-feature` | `/search-issues` | Refined stories → `/story-full` |
| `/create-epic` | `/search-issues` | `/verify-issue` >= 90% |
| `/story-full` | `/search-issues` | `/verify-issue --with-subtasks` >= 90% |
| `/analyze-story` | Story exists | `/verify-issue --with-subtasks` >= 90% |
| `/create-testplan` | Story exists | `/verify-issue` >= 90% |
| `/create-task` | `/search-issues` | `/verify-issue` >= 90% |
| `/update-{type}` | Issue exists | `/verify-issue` >= 90% |
| `/sync-alignment` | Story/artifacts changed | `/verify-issue --with-subtasks` >= 90% |
| `/plan-sprint` | Sprint exists | — |
| `/dependency-chain` | Sprint planned | — |

## Repomix Context Packs

> Load shared-references as a single Repomix pack instead of 4-5 individual Read calls.
> Packs defined in `shared-references/context-packs.json`.

### Usage

```text
1. Determine workflow type (story, subtask, sprint, verify, etc.)
2. Look up pack in context-packs.json → get file list
3. Call mcp__repomix__pack_codebase with includePatterns from pack
4. Use read_repomix_output or grep_repomix_output for targeted lookups
```

### Example: story workflow

```text
mcp__repomix__pack_codebase(
  directory: ".claude/skills/shared-references",
  includePatterns: "templates.md,verification-checklist.md,vertical-slice-guide.md,writing-style.md",
  compress: true
)
→ Single packed output replaces 4 Read calls
→ Tree-sitter compression reduces tokens ~40-60%
```

### When to Use Repomix vs Direct Read

| Situation | Use |
| --- | --- |
| Need 3+ shared-references files | Repomix pack |
| Need 1-2 specific files | Direct Read |
| Need to search across files | `grep_repomix_output` |
| Exploring target project codebase | Task(Explore) — Repomix insufficient |

### Pack Types

| Pack | Files | Use Case |
| --- | --- | --- |
| `story` | templates, verification, vertical-slice, writing-style | Create/update stories |
| `subtask` | templates, verification, tools, vertical-slice | Analyze story → subtasks |
| `epic` | templates, verification, writing-style | Create/update epics |
| `sprint` | sprint-frameworks, team-capacity, dependency, tools | Sprint planning |
| `verify` | jql-quick-ref, verification, templates, writing-style | Verify issue quality |
| `sync` | templates, verification, tools, orchestration | Cascade/sync alignment |

## Cache Hygiene

- After any MCP write (`jira_update_issue`, `jira_create_issue`) → `cache_invalidate(issue_key)`
- After sprint manipulation → `cache_invalidate(sprint_id)`
- Before sprint planning → `cache_refresh(sprint_id)` for fresh data
