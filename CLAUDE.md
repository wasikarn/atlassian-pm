# CLAUDE.md

## Overview

**Prefer retrieval-led reasoning:** search project docs (`references/`, qmd, `cache_get_issue`) and explore codebase before generating answers from training knowledge. When uncertain, retrieve first — don't guess.

Agile Documentation System — skills-based Jira/Confluence automation

**Plugin:** `atlassian-pm` · **Structure:** `SKILL.md` → phases → `references/` (24 docs) | `scripts/` (api/, lib/, sprint/, analysis/, docs/) | `mcp-servers/atlassian-cache/` (MCP) | `hooks/` (44 hooks in `plugin/` + `dev/`) | `agents/` (18)
**Skills layout:** 31 skills at `skills/{setup,epic,story,task,sprint,confluence,utilities}/<name>/SKILL.md` · shared refs at `../../../references/` from each skill · each skill has `## 🎓 Domain Expert Notes` (frameworks, metrics, failure modes)

**New here?** Start with [QUICKSTART.md](QUICKSTART.md) → then `/atlassian-pm:doctor` to verify setup.
**Skill index:** [skills/README.md](skills/README.md) — all 31 skills with phases, categories, and argument patterns.
**Hook reference:** [hooks/README.md](hooks/README.md) — all 44 hooks, what they enforce, and how to debug them.

## Project Settings

Core config (jira fields, team roster, services, environments): @.claude/project-config.json
Team detail (git evidence, capacity model, bus factor — load on-demand for sprint planning): `.claude/project-config-team-detail.json` *(gitignored — create from `.claude/project-config-team-detail.json.template`)*

**Dynamic lookup:** Board → `jira_get_agile_boards(project_key=<from config>)` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`
**Prerequisites:** `acli` CLI, MCP (Jira + Confluence + Figma + GitHub), Python 3.x
**Git filters:** smudge/clean auto-convert placeholders↔real values · `./scripts/setup.sh` to configure
**Versioning:** `./scripts/bump-version.sh <X.Y.Z>` — updates marketplace.json + README badge, commits, tags, pushes, creates GitHub release, updates plugin + copies config in one step
**Plugin mode:** `claude --plugin-dir .` (dev) · Skills namespaced as `/atlassian-pm:<name>`

**Workflows:** [`skill-orchestration.md`](references/skill-orchestration.md) — how skills chain together · [`workflow-patterns.md`](references/workflow-patterns.md) — gate levels, QG scoring, annotation cycle
**Verify:** `/atlassian-pm:verify-issue` flags: `--with-subtasks` | `--fix` | `--dry-run`

**Tool selection:** `.claude/rules/tool-selection.md` · `.claude/rules/mermaid.md` · `.claude/rules/python-scripts.md` (3 auto-loaded rules) · `references/tools.md` (field presets)

## Common Mistakes

> Hook-enforced mistakes (HR2-HR7, HR10) are blocked automatically. Full troubleshooting: `references/troubleshooting.md`

| Category | Quick Fix |
| --- | --- |
| Set parent on existing issue | MCP/acli silently fail → use `jira_set_parent.py --issues KEY --parent EPIC` |
| Sibling tool call errored | One parallel MCP call failed → all cancelled. Fix failing call first |
| Mermaid / Confluence issues | See `mermaid-guide.md` + `.claude/rules/mermaid.md` + `troubleshooting.md` |

## References

Loaded on demand from `references/` (24 docs, indexed by `templates.md`). **Scripts:** `skills/utilities/atlassian-scripts/SKILL.md` → `scripts/api/`

## Core Principles

| Principle | Rule |
| --- | --- |
| QG first | NEVER create/edit Atlassian issues before QG ≥ 90% |
| Phase order | Follow phases in order, never skip steps |
| Traceability | Everything links to parent: Sub-task→Story→Epic |
| Explore first | Prefer `Task(Explore)` before creating Sub-tasks (no explore = generic paths) |

### HARD RULES

> Hooks enforce HR2-HR7, HR10 automatically. Full definitions: `references/hr-rules.md`

| Rule | Constraint |
| --- | --- |
| **HR1** QG ≥ 90% | NEVER write before QG pass. Flow: Explore→ADF→QG≥90%→MCP shell→acli edit. |
| **HR2** JQL parent | NEVER `ORDER BY` with `parent =`, `parent in`, `key in (...)` — parser error |
| **HR3** Assignee | MCP assignee silently fails. Use `acli jira workitem assign -k "KEY" -a "email" -y` |
| **HR4** Confluence macros | MCP HTML-escapes macros → raw XML. Use `update_page_storage.py` for ToC/Children/Code |
| **HR5** Subtask parent | MCP may silently ignore parent → orphan. MCP create+verify parent → acli edit. |
| **HR6** Cache invalidate | After any MCP write → `cache_invalidate(issue_key)`. Stale reads corrupt verify/cascade/planning |
| **HR7** Sprint ID | NEVER hardcode. Always `jira_get_sprints_from_board()`. Wrong sprint = silent failure |
| **HR8** Subtask alignment | Dates within parent range. SP sum ≈ parent. Misalignment → wrong burndown. |
| **HR9** Desc alignment | Story ACs covered by subtask objectives. Epic scope in children. `/atlassian-pm:verify-issue --with-subtasks` (A1-A6) |
| **HR10** Subtask sprint | NEVER set `{{SPRINT_FIELD}}` on subtasks — inherited from parent. API error + cascade failure. |

## Context Management

**Compaction:** Preserve: modified files + issue keys · pending HR5/HR6 ops · active skill phase · sprint IDs. Hooks re-inject HR reminders via `plugin/session/post_compact_reinject.py`.

**Subagents:** Use `agents/` for isolated investigation — keeps main context clean. Available: `code-explorer` (haiku), `jira-search` (haiku), `issue-bootstrap` (haiku), `quality-gate` (sonnet), `pr-description-writer` (haiku), `pr-review-jira-sync` (haiku), `velocity-tracker` (haiku), `story-writer` (sonnet), `alignment-checker` (sonnet), `backlog-groomer` (sonnet), `retrospective-analyst` (sonnet), `sprint-planner` (sonnet), `estimation-calibrator` (haiku, L3), `risk-forecaster` (sonnet, L3), `adf-surgeon` (haiku, L3), `team-pattern-advisor` (sonnet, L3), `sprint-transition-agent` (haiku) — batch sprint issue moves + sprint state transitions; used by close-sprint Phase 4, `spec-parser-agent` (haiku, L1) — parse Confluence page content into structured requirements (personas, requirements, constraints); used by spec-to-stories Phase 2; receives pre-fetched content, tools: Read only.

Run `/optimize-context` when CLAUDE.md feels outdated or context exceeds 15 KB.

## Efficiency

- **No redundant reads:** Summarize `references/` on first read — never re-read same file.
- **Deliverable-first:** Every skill must produce its deliverable (ADF JSON, issue, report) within the session — don't stop at research phase.
- **Simple patterns:** Prefer `*.md` over complex globs. Default to simplest pattern that works.
- **Validate before commit:** Check frontmatter fields, `allowed-tools`, hook commands. Run markdownlint on `*.md` changes.
