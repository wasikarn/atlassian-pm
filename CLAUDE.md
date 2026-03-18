# CLAUDE.md

## Overview

**Prefer retrieval-led reasoning:** search project docs (`shared-references/`, qmd, `cache_get_issue`) and explore codebase before generating answers from training knowledge. When uncertain, retrieve first — don't guess.

Agile Documentation System for **{{COMPANY}} Platform** — skills-based Jira/Confluence automation

**Plugin:** `atlassian-pm` · **Structure:** `SKILL.md` → phases → `skills/shared-references/` (23 docs) | `skills/atlassian-scripts/` (16 scripts) | `mcp-servers/jira-cache-server/` (MCP) | `hooks/` (39) | `agents/` (8) | `tasks/` (ADF JSON) | `scripts/` (setup/sprint/confluence)

## Project Settings

Full config (team, fields, services, environments): @.claude/project-config.json

**Dynamic lookup:** Board → `jira_get_agile_boards(project_key="{{PROJECT_KEY}}")` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`
**Prerequisites:** `acli` CLI, MCP (Jira + Confluence + Figma + GitHub), Python 3.x
**Git filters:** smudge/clean auto-convert placeholders↔real values · `./scripts/setup.sh` to configure
**Plugin mode:** `claude --plugin-dir .` (dev) · Skills namespaced as `/atlassian-pm:<name>`

## Skill Commands

| Command | Description |
| --- | --- |
| `/atlassian-pm:feature-blueprint` | Multi-perspective blueprint (PO×Domain×TL×Eng×QA) → Confluence doc + backlog map |
| `/atlassian-pm:refine-feature` | Multi-role debate (PO×TL×Eng×QA) → refined stories |
| `/atlassian-pm:create-epic` | Create Epic from product vision + Epic Doc |
| `/atlassian-pm:create-task` | Create Task (tech-debt, bug, chore, spike) |
| `/atlassian-pm:analyze-story {{PROJECT_KEY}}-XXX` | Analyze Story → Sub-tasks + Technical Note |
| `/atlassian-pm:create-testplan {{PROJECT_KEY}}-XXX` | Create Test Plan → [QA] Sub-task |
| `/atlassian-pm:create-doc` | Create Confluence page (tech-spec, adr, parent) |
| `/atlassian-pm:update-{epic,story,task,subtask}` | Edit single issue — scope, AC, format |
| `/atlassian-pm:update-doc PAGE-ID` | Update/Move Confluence page |
| `/atlassian-pm:story-full` | Create Story + Sub-tasks in one go (preferred) |
| `/atlassian-pm:sync-alignment {{PROJECT_KEY}}-XXX` | Sync all artifacts bidirectional (Story+Sub-tasks, or +Confluence) |
| `/atlassian-pm:assign {{PROJECT_KEY}}-XXX name` | Quick assign issue (HR3-safe, uses acli) |
| `/atlassian-pm:plan-sprint` | Sprint planning: carry-over + capacity + assign |
| `/atlassian-pm:dependency-chain` | Dependency analysis, critical path, swim lanes |
| `/atlassian-pm:search-issues` | Search before creating (dedup) |
| `/atlassian-pm:verify-issue {{PROJECT_KEY}}-XXX` | Verify quality (ADF, INVEST, language) |
| `/atlassian-pm:activity-report` | Generate activity report from claude-mem |
| `/optimize-context` | Audit + compress CLAUDE.md |

`/atlassian-pm:verify-issue` flags: `--with-subtasks` (batch) | `--fix` (auto-fix) | `--dry-run` (report only)

## Workflow Chain

| Phase | Flow | Notes |
| --- | --- | --- |
| **Search first** | `/atlassian-pm:search-issues` | Always run before creating (dedup) |
| **Blueprint** | `/atlassian-pm:feature-blueprint` → `/atlassian-pm:create-epic` → `/atlassian-pm:story-full` | Greenfield / architecture review |
| **Refine** | `/atlassian-pm:refine-feature` → `/atlassian-pm:story-full` | Unclear/complex/multi-service |
| **Create** | PM `/atlassian-pm:create-epic` → `/atlassian-pm:story-full` → QA `/atlassian-pm:create-testplan` | QA optional |
| **Update single** | `/atlassian-pm:update-{epic,story,task,subtask}` | One issue |
| **Update cascade** | `/atlassian-pm:sync-alignment` = Story + Sub-tasks (+ Confluence if exists) | |
| **Standalone** | `/atlassian-pm:create-task`, `/atlassian-pm:create-doc`, `/atlassian-pm:update-doc` | |
| **Planning** | `/atlassian-pm:plan-sprint` | |
| **Verify** | `/atlassian-pm:verify-issue` | Always run after creating/updating |

**Full orchestration:** `skills/shared-references/skill-orchestration.md`

## Tool Selection

| Operation | Tool | Notes |
| --- | --- | --- |
| Description | `acli --from-json` (ADF JSON) | Fields: MCP `jira_update_issue` |
| Read issue | `cache_get_issue` → `jira_get_issue` | Always use `fields` param |
| Search | `cache_search` / `cache_text_search` → `jira_search` | Always use `fields` + `limit` |
| Comment | MCP `jira_add_comment` | |
| Sub-task | Two-Step: MCP create → acli edit | `parent` doesn't work with acli |
| Script | `update_jira_description.py` (REST) | `/atlassian-pm:atlassian-scripts` for format |
| Confluence | MCP (read/simple), Python scripts (code/macros) | `audit_confluence_pages.py` (audit) |
| Confluence (advanced) | See `troubleshooting.md` + `mermaid-guide.md` | Page appearance, Mermaid, ADF panels |
| Explore | Task(Explore) | Always before creating subtasks |
| Parent (Epic) | `jira_set_parent.py` (REST) | MCP/acli silently ignore parent field on existing issues |
| Issue Links | MCP `jira_create_issue_link` | Blocks/Relates · `jira_create_remote_issue_link` (web) |
| Sprint | Agile REST via `JiraAPI._request()` | MCP can't move to backlog |
| Sprint batch | `scripts/sprint/` | `clear_sprint_dates.py`, `sprint_set_fields.py`, `sprint_rank_by_date.py`, `sprint_subtask_alignment.py`, `update_sprint_goals.py` |
| Cache | MCP `jira-cache-server` (8 tools) | `force_refresh=true` after web edits or "ล่าสุด/refresh/stale" |

### Field & ADF Quick Reference

**`jira_get_issue`** — always use `fields` param · **`jira_search`** — always use `fields` + `limit` params → see `skills/shared-references/tools.md` for preset tables

**ADF CREATE vs EDIT differ** — CREATE: `projectKey`+`type`+`summary`+`description` (no `issues`) · EDIT: `issues`+`description` (no `projectKey`/`type`/`summary`/`parent`) → details in `skills/shared-references/templates-core.md`
**Subtask Two-Step:** MCP create (with `parent:{key:"{{PROJECT_KEY}}-XXX"}`) → acli `workitem edit --from-json`
**Smart Link:** see `skills/shared-references/templates-core.md` for inlineCard format

## Common Mistakes

> Hook-enforced mistakes (HR2-HR7, HR10) are blocked automatically — see `hooks/`. Full troubleshooting: `skills/shared-references/troubleshooting.md`

| Category | Quick Fix |
| --- | --- |
| Subtask parent → error | `additional_fields={"parent": {"key": "{{PROJECT_KEY}}-XXX"}}` |
| Set parent on existing issue | MCP/acli silently fail → use `jira_set_parent.py --issues KEY --parent EPIC` |
| `fields` param → error | Use `additional_fields` not `fields` |
| `project_key_or_id` → error | Use `project_key` |
| `limit > 50` → error | Max 50, use pagination `start_at` |
| Sibling tool call errored | One parallel MCP call failed → all cancelled. Fix failing call first |
| Mermaid / Confluence issues | See `mermaid-guide.md` + `.claude/rules/mermaid.md` + `troubleshooting.md` for rendering, animation, panels, font-size |

## References

Loaded on demand from `skills/shared-references/` (23 docs, indexed by `templates.md`). **Scripts:** `skills/atlassian-scripts/SKILL.md`

## Core Principles

1. **Quality Gate before Atlassian** — NEVER create/edit issues on Jira/Confluence before QG ≥ 90%
2. **Phase-based workflows** — follow phases in order, never skip steps
3. **Clear handoffs** — each role passes structured context to next
4. **Traceability** — everything links back to parent (Story→Epic, Sub-task→Story)
5. **Explore first** — prefer `Task(Explore)` before creating Sub-tasks (no explore = generic paths)

### HARD RULES

Rules causing **silent failures**, **data corruption**, or **irreversible damage**. Hooks enforce HR2-HR7, HR10 automatically.

> Full definitions, examples, and enforcement details: `skills/shared-references/hr-rules.md`

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

**Compaction:** Preserve: modified files + issue keys · pending HR5/HR6 ops · active skill phase · sprint IDs. Hooks re-inject HR reminders via `post-compact-reinject.py`.

**Subagents:** Use `agents/` for isolated investigation — keeps main context clean. Available: `code-explorer` (haiku), `issue-reader` (haiku), `jira-search` (haiku), `issue-bootstrap` (haiku), `quality-gate` (haiku), `story-writer` (sonnet), `alignment-checker` (sonnet), `sprint-planner` (opus).

Run `/optimize-context` when CLAUDE.md feels outdated or context exceeds 15 KB.

## Efficiency

- **No redundant reads:** Summarize `skills/shared-references/` on first read — never re-read same file.
- **Deliverable-first:** Every skill must produce its deliverable (ADF JSON, issue, report) within the session — don't stop at research phase.
- **Simple patterns:** Prefer `*.md` over complex globs. Default to simplest pattern that works.
- **Validate before commit:** Check frontmatter fields, `allowed-tools`, hook commands. Run markdownlint on `*.md` changes.
