# Skill Orchestration

> Intent-to-skill mapping, quality gates, and decision trees.
> Read this before creating/editing Jira issues.

## Intent-to-Skill Map

| Intent | Skill Chain | Gate |
| --- | --- | --- |
| Feature blueprint | `/blueprint` → `/create-epic` → `/create-story` → verify | ≥ 90% (Confluence) |
| Refine feature | `/search-issues` → `/refine-epic` → `/create-story` → verify | N/A (pre-creation) |
| Create epic | `/search-issues` → `/create-epic` → verify | ≥ 90% |
| Create story | `/search-issues` → `/create-story` → verify | ≥ 90% |
| Create task | `/search-issues` → `/create-task` → verify | ≥ 90% |
| Analyze story | `/analyze-story` → verify `--with-subtasks` | ≥ 90% |
| Test plan | `/create-testplan` → verify | ≥ 90% |
| Update single | `/update-{epic,story,task,subtask}` → verify | ≥ 90% |
| Update cascade | `/sync-artifacts` → verify `--with-subtasks` | ≥ 90% |
| Board replenishment | `/flow-check --replenish` | N/A |
| Dependency check | `/map-dependencies` | N/A |
| Close sprint | `/close-sprint` → `/retrospective-analyst` | N/A |
| Close sprint + action items | `/sprint-close-full-with-actions` (chains: close-sprint → retrospective-analyst → retro-actions) | N/A |
| Daily standup | `/standup-report` | N/A |
| Daily ops | `/daily-ops` (chains: standup-report → flow-check → blockers synthesis) | N/A |
| Release planning | `/plan-release` | N/A |
| Bulk reschedule | `/reschedule-sprint` | N/A |
| Import spec | `/spec-to-stories` → `/create-story` (per story) | ≥ 90% |
| Tech debt audit | `/scan-tech-debt` → `/create-task` (prioritized) | N/A |
| Bug triage | `/search-issues` → `/bug-triage` → `/create-testplan` (after fix) | ≥ 90% |
| Release notes | `/plan-release` → `/close-sprint` → `/release-notes` | N/A |
| Start ticket (DLC) | `/start-ticket` | pre: ticket in Jira · post: status = In Progress, AC displayed |
| Ship to QA (DLC) | `/ship-to-qa` | pre: PR open, branch deployed · post: Jira comment posted, status = Ready for QA |

**Rules:**

- Always `/search-issues` before creating (dedup)
- Always `/verify-issue` after creating/editing
- Use `/create-story` for new stories (combines PO + TA). Use `/analyze-story` only for existing stories needing subtasks

## HARD RULES

> Full definitions and rationale: [hr-rules.md](hr-rules.md)

### QG Scoring Reference

| Score | Status | Action |
| --- | --- | --- |
| 90-100% | Pass | Send to Atlassian |
| 70-89% | Warning | Auto-fix, then re-score |
| < 70% | Fail | Must fix, ask user if stuck |

| Check | Max | Applies To |
| --- | --- | --- |
| T1-T5 Technical | 5 | All types |
| S1-S5 Story Quality | 6 | Story |
| ST1-ST5 Subtask Quality | 5 | Sub-task |
| QA1-QA5 QA Quality | 5 | QA Sub-task |
| B1-B8 Blueprint Quality | 8 (or 5 for S-tier) | Blueprint (Confluence) |
| E1-E4 Epic Quality | 4 | Epic |
| A1-A6 Alignment | 6 | `--with-subtasks` only |

Full checklist: [verification-checklist.md](verification-checklist.md)

## Decision Trees

### Create or Update?

```mermaid
flowchart TD
    A{New Requirement?} -->|Yes| B["/search-issues\ndedup check"]
    A -->|"No — Edit existing"| C{Single or Cascade?}

    B --> D{Duplicate found?}
    D -->|Yes| E["/update-* or /sync-artifacts"]
    D -->|No| F{Scope?}

    F -->|"Greenfield / Architecture\nNew domain"| G["/blueprint\n→ /create-epic → /create-story"]
    F -->|"Unclear scope\nMulti-service / High-risk"| H["/refine-epic\n→ /create-story"]
    F -->|"Clear scope\nSingle service"| I["/create-story ⭐ preferred"]
    F -->|"Bug / Tech-debt\nChore / Spike"| J["/create-task"]

    C -->|Single issue| K["/update-{type}"]
    C -->|"Story needs new Sub-tasks"| L["/analyze-story"]
    C -->|"Story + Sub-tasks sync"| M["/sync-artifacts"]

    classDef skill fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    class E,G,H,I,J,K,L,M skill
```

### create-story vs analyze-story?

```mermaid
flowchart LR
    A{Story exists in Jira?} -->|"No\nCreate from scratch"| B
    A -->|"Yes\nNeed subtasks only"| C

    B["/create-story ⭐ default\nPhases 1–10\nPO + TA combined\nOutput: Story + Sub-tasks"]
    C["/analyze-story\nPhases 5–10\nSkips story creation\nStarts from impact analysis"]

    classDef skill fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    class B,C skill
```

## Pre/Post Conditions

| Skill | Pre-condition | Post-condition |
| --- | --- | --- |
| `/blueprint` | Feature idea / concept | Confluence page + backlog map → `/create-epic` → `/create-story` |
| `/refine-epic` | `/search-issues` | Refined stories → `/create-story` |
| `/create-epic` | `/search-issues` | `/verify-issue` >= 90% |
| `/create-story` | `/search-issues` | `/verify-issue --with-subtasks` >= 90% |
| `/analyze-story` | Story exists | `/verify-issue --with-subtasks` >= 90% |
| `/create-testplan` | Story exists | `/verify-issue` >= 90% |
| `/create-task` | `/search-issues` | `/verify-issue` >= 90% |
| `/update-{type}` | Issue exists | `/verify-issue` >= 90% |
| `/sync-artifacts` | Story/artifacts changed | `/verify-issue --with-subtasks` >= 90% |
| `/start-ticket` | Issue key exists in Jira | Ticket → In Progress + AC displayed |
| `/ship-to-qa` | PR open, issue In Progress | Jira comment (PR + preview URLs) + ticket → Ready for QA |
| `/flow-check` | Board config in project-config.json | WIP table + optional replenishment |
| `/map-dependencies` | Issues with links in Jira | Dependency graph + critical path |
| `/close-sprint` | Active sprint with issues | Closed sprint + Confluence review page |
| `/retro-actions` | action-items block from retrospective-analyst or Confluence page | Jira tasks created per action item, linked to sprint |
| `/epic-health` | Epic key or active epics | Coverage/SP/timeline audit report |
| `/standup-report` | Active sprint | Digest output (optional Confluence post) |
| `/plan-release` | Epics with SP estimates | Confluence release plan + Jira Fix Version |
| `/reschedule-sprint` | Issues with dates | Updated dates + HR8 alignment |
| `/spec-to-stories` | Confluence page + epic | Jira User Stories linked to epic |
| `/scan-tech-debt` | Project with tech-debt issues | Confluence priority matrix page |

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
- Before flow-check or map-dependencies → `cache_refresh(sprint_id)` for fresh data
