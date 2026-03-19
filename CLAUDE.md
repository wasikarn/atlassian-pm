# CLAUDE.md

## Overview

**Prefer retrieval-led reasoning:** search project docs (`shared-references/`, qmd, `cache_get_issue`) and explore codebase before generating answers from training knowledge. When uncertain, retrieve first — don't guess.

Agile Documentation System — skills-based Jira/Confluence automation

**Plugin:** `atlassian-pm` · **Structure:** `SKILL.md` → phases → `skills/shared-references/` (23 docs) | `skills/atlassian-scripts/` (16 scripts) | `mcp-servers/jira-cache-server/` (MCP) | `hooks/` (40 scripts) | `agents/` (8) | `scripts/` (setup/sprint/parse)

## Project Settings

Core config (jira fields, team roster, services, environments): @.claude/project-config.json
Team detail (git evidence, capacity model, bus factor — load on-demand for sprint planning): `.claude/project-config-team-detail.json`

**Dynamic lookup:** Board → `jira_get_agile_boards(project_key="{{PROJECT_KEY}}")` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`
**Prerequisites:** `acli` CLI, MCP (Jira + Confluence + Figma + GitHub), Python 3.x
**Git filters:** smudge/clean auto-convert placeholders↔real values · `./scripts/setup.sh` to configure
**Plugin mode:** `claude --plugin-dir .` (dev) · Skills namespaced as `/atlassian-pm:<name>`

**Workflows:** `skills/shared-references/skill-orchestration.md` · `/atlassian-pm:verify-issue` flags: `--with-subtasks` | `--fix` | `--dry-run`

**Tool selection:** `.claude/rules/tool-selection.md` (auto-loaded for skills/hooks/scripts) · `skills/shared-references/tools.md` (field presets)

## Common Mistakes

> Hook-enforced mistakes (HR2-HR7, HR10) are blocked automatically. Full troubleshooting: `skills/shared-references/troubleshooting.md`

| Category | Quick Fix |
| --- | --- |
| Set parent on existing issue | MCP/acli silently fail → use `jira_set_parent.py --issues KEY --parent EPIC` |
| Sibling tool call errored | One parallel MCP call failed → all cancelled. Fix failing call first |
| Mermaid / Confluence issues | See `mermaid-guide.md` + `.claude/rules/mermaid.md` + `troubleshooting.md` |

## References

Loaded on demand from `skills/shared-references/` (23 docs, indexed by `templates.md`). **Scripts:** `skills/atlassian-scripts/SKILL.md`

## Core Principles

| Principle | Rule |
| --- | --- |
| QG first | NEVER create/edit Atlassian issues before QG ≥ 90% |
| Phase order | Follow phases in order, never skip steps |
| Traceability | Everything links to parent: Sub-task→Story→Epic |
| Explore first | Prefer `Task(Explore)` before creating Sub-tasks (no explore = generic paths) |

### HARD RULES

> Hooks enforce HR2-HR7, HR10 automatically. Full definitions: `skills/shared-references/hr-rules.md`

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

**Compaction:** Preserve: modified files + issue keys · pending HR5/HR6 ops · active skill phase · sprint IDs. Hooks re-inject HR reminders via `post_compact_reinject.py`.

**Subagents:** Use `agents/` for isolated investigation — keeps main context clean. Available: `code-explorer` (haiku), `issue-reader` (haiku), `jira-search` (haiku), `issue-bootstrap` (haiku), `quality-gate` (haiku), `story-writer` (sonnet), `alignment-checker` (sonnet), `sprint-planner` (opus).

Run `/optimize-context` when CLAUDE.md feels outdated or context exceeds 15 KB.

## Efficiency

- **No redundant reads:** Summarize `skills/shared-references/` on first read — never re-read same file.
- **Deliverable-first:** Every skill must produce its deliverable (ADF JSON, issue, report) within the session — don't stop at research phase.
- **Simple patterns:** Prefer `*.md` over complex globs. Default to simplest pattern that works.
- **Validate before commit:** Check frontmatter fields, `allowed-tools`, hook commands. Run markdownlint on `*.md` changes.
