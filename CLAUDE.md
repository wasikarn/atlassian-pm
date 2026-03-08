# CLAUDE.md

## Overview

**Prefer retrieval-led reasoning:** search project docs (`shared-references/`, qmd, `cache_get_issue`) and explore codebase before generating answers from training knowledge. When uncertain, retrieve first — don't guess.

Agile Documentation System for **{{COMPANY}} Platform** — skills-based Jira/Confluence automation

**Structure:** `.claude/skills/` — 23 skills (`SKILL.md` → phases → `shared-references/`) + `atlassian-scripts/` (16 Python scripts) + `jira-cache-server/` (MCP) + `shared-references/` (19 docs)

```text
.claude/skills/{name}/SKILL.md     ← skill entry (reads shared-references/)
.claude/skills/shared-references/  ← 19 docs: templates, tools, verification, orchestration
.claude/skills/atlassian-scripts/  ← 16 Python scripts + lib/ (REST API)
.claude/skills/jira-cache-server/  ← MCP server (SQLite + FTS5, local Jira cache)
.claude/hooks/                     ← 37 Python hooks (HR enforcement + automation)
.claude/agents/                    ← 7 subagent definitions (haiku/sonnet/opus)
tasks/                             ← ADF JSON output (acli --from-json input)
scripts/                           ← setup, sync + sprint/, confluence/, archive/
```

## Project Settings

Full config (team, fields, services, environments): @.claude/project-config.json

**Dynamic lookup:** Board → `jira_get_agile_boards(project_key="{{PROJECT_KEY}}")` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`
**Prerequisites:** `acli` CLI, MCP (Jira + Confluence + Figma + GitHub), Python 3.x
**Git filters:** smudge/clean auto-convert placeholders↔real values · `./scripts/setup.sh` to configure

## Skill Commands

| Command | Description |
| --- | --- |
| `/jira-create-epic` | Create Epic from product vision + Epic Doc |
| `/jira-create-story` | Create User Story from requirements |
| `/jira-create-task` | Create Task (tech-debt, bug, chore, spike) |
| `/jira-analyze-story {{PROJECT_KEY}}-XXX` | Analyze Story → Sub-tasks + Technical Note |
| `/jira-create-testplan {{PROJECT_KEY}}-XXX` | Create Test Plan → [QA] Sub-task |
| `/confluence-create-doc` | Create Confluence page (tech-spec, adr, parent) |
| `/jira-update-{epic,story,task,subtask}` | Edit single issue — scope, AC, format |
| `/confluence-update-doc PAGE-ID` | Update/Move Confluence page |
| `/jira-story-full` | Create Story + Sub-tasks in one go (preferred) |
| `/jira-story-cascade {{PROJECT_KEY}}-XXX` | Update Story + cascade to Sub-tasks |
| `/jira-sync-alignment {{PROJECT_KEY}}-XXX` | Sync all artifacts bidirectional |
| `/jira-assign {{PROJECT_KEY}}-XXX name` | Quick assign issue (HR3-safe, uses acli) |
| `/jira-plan-sprint` | Sprint planning: carry-over + capacity + assign |
| `/jira-dependency-chain` | Dependency analysis, critical path, swim lanes |
| `/jira-search-issues` | Search before creating (dedup) |
| `/jira-verify-issue {{PROJECT_KEY}}-XXX` | Verify quality (ADF, INVEST, language) |
| `/jira-activity-report` | Generate activity report from claude-mem |
| `/optimize-context` | Audit + compress CLAUDE.md |

`/jira-verify-issue` flags: `--with-subtasks` (batch) | `--fix` (auto-fix) | `--dry-run` (report only)

## Workflow Chain

| Phase | Flow | Notes |
| --- | --- | --- |
| **Search first** | `/jira-search-issues` | Always run before creating (dedup) |
| **Create** | PM `/jira-create-epic` → PO `/jira-create-story` → TA `/jira-analyze-story` → QA `/jira-create-testplan` | QA optional |
| **Combined** | `/jira-story-full` = `/jira-create-story` + `/jira-analyze-story` in one go | Preferred |
| **Update single** | `/jira-update-{epic,story,task,subtask}` | One issue |
| **Update cascade** | `/jira-story-cascade` = Story + Sub-tasks | `/jira-sync-alignment` if Confluence too |
| **Standalone** | `/jira-create-task`, `/confluence-create-doc`, `/confluence-update-doc` | |
| **Planning** | `/jira-plan-sprint` | Reads Jira, assigns work |
| **Verify** | `/jira-verify-issue` | Always run after creating/updating |

**Full orchestration:** `shared-references/skill-orchestration.md`

## Tool Selection

| Operation | Tool | Notes |
| --- | --- | --- |
| Description | `acli --from-json` (ADF JSON) | Fields: MCP `jira_update_issue` |
| Read issue | `cache_get_issue` → `jira_get_issue` | Always use `fields` param |
| Search | `cache_search` / `cache_text_search` → `jira_search` | Always use `fields` + `limit` |
| Comment | MCP `jira_add_comment` | |
| Sub-task | Two-Step: MCP create → acli edit | `parent` doesn't work with acli |
| Script | `update_jira_description.py` (REST) | `/atlassian-scripts` for format |
| Confluence | MCP (read/simple), Python scripts (code/macros) | `audit_confluence_pages.py` (audit) |
| Confluence (advanced) | See `shared-references/troubleshooting.md` | Page appearance, Mermaid diagrams, ADF panel fix — details in troubleshooting + `mermaid-guide.md` |
| Explore | Task(Explore) | Always before creating subtasks |
| Parent (Epic) | `jira_set_parent.py` (REST) | MCP/acli silently ignore parent field on existing issues |
| Issue Links | MCP `jira_create_issue_link` | Blocks/Relates · `jira_create_remote_issue_link` (web) |
| Sprint | Agile REST via `JiraAPI._request()` | MCP can't move to backlog |
| Sprint batch | `scripts/sprint/` utilities | `clear_sprint_dates`, `sprint_set_fields`, `sprint_rank_by_date`, `sprint_subtask_alignment` |
| Cache | MCP `jira-cache-server` (8 tools) | `force_refresh=true` after web edits or "ล่าสุด/refresh/stale" |

### Field & ADF Quick Reference

**`jira_get_issue`** — always use `fields` param · **`jira_search`** — always use `fields` + `limit` params → see `shared-references/tools.md` for preset tables

**ADF CREATE vs EDIT differ** — CREATE: `projectKey`+`type`+`summary`+`description` (no `issues`) · EDIT: `issues`+`description` (no `projectKey`/`type`/`summary`/`parent`) → details in `shared-references/templates-core.md`
**Subtask Two-Step:** MCP create (with `parent:{key:"{{PROJECT_KEY}}-XXX"}`) → acli `workitem edit --from-json`
**Smart Link:** see `shared-references/templates-core.md` for inlineCard format

## Common Mistakes

> Hook-enforced mistakes (HR2-HR7, HR10) are blocked automatically — see `.claude/hooks/`. Full troubleshooting: `shared-references/troubleshooting.md`

| Category | Quick Fix |
| --- | --- |
| Subtask parent → error | `additional_fields={"parent": {"key": "{{PROJECT_KEY}}-XXX"}}` |
| Set parent on existing issue | MCP/acli silently fail → use `jira_set_parent.py --issues KEY --parent EPIC` |
| `fields` param → error | Use `additional_fields` not `fields` |
| `project_key_or_id` → error | Use `project_key` |
| `limit > 50` → error | Max 50, use pagination `start_at` |
| Sibling tool call errored | One parallel MCP call failed → all cancelled. Fix failing call first |
| Prefer `/jira-story-full` | `/jira-search-issues` → `/jira-story-full` → `/jira-verify-issue` |
| Mermaid / Confluence issues | See `mermaid-guide.md` + `.claude/rules/mermaid.md` + `troubleshooting.md` for rendering, animation, panels, font-size |

## References

Key shared references (loaded by skills on demand):
- Templates: @.claude/skills/shared-references/templates.md
- Writing style: @.claude/skills/shared-references/writing-style.md
- Tools: @.claude/skills/shared-references/tools.md
- Troubleshooting: @.claude/skills/shared-references/troubleshooting.md

Other refs: `.claude/skills/shared-references/` (19 docs, indexed by `templates.md`) | **Scripts:** `atlassian-scripts/SKILL.md`
- Mermaid diagrams: @.claude/skills/shared-references/mermaid-guide.md

## Core Principles

1. **Quality Gate before Atlassian** — NEVER create/edit issues on Jira/Confluence before QG ≥ 90%
2. **Phase-based workflows** — follow phases in order, never skip steps
3. **Clear handoffs** — each role passes structured context to next
4. **Traceability** — everything links back to parent (Story→Epic, Sub-task→Story)
5. **Explore first** — prefer `Task(Explore)` before creating Sub-tasks (no explore = generic paths)

### HARD RULES

Rules causing **silent failures**, **data corruption**, or **irreversible damage**. Hooks enforce HR2-HR7, HR10 automatically.

| Rule | Constraint |
| --- | --- |
| **HR1** QG ≥ 90% | NEVER write to Jira/Confluence before QG pass. Flow: Explore → ADF → QG ≥ 90% → MCP shell (no desc) → acli edit. All create/update skills. |
| **HR2** JQL parent | NEVER `ORDER BY` with `parent =`, `parent in`, `key in (...)` — parser error |
| **HR3** Assignee | MCP assignee silently fails. Use `acli jira workitem assign -k "KEY" -a "email" -y` |
| **HR4** Confluence macros | MCP HTML-escapes macros → raw XML. Use `update_page_storage.py` for ToC/Children/Code |
| **HR5** Subtask parent | MCP may silently ignore parent → orphan. (1) MCP create with parent, (2) verify parent set, (3) acli edit |
| **HR6** Cache invalidate | After any MCP write → `cache_invalidate(issue_key)`. Stale reads corrupt verify/cascade/planning |
| **HR7** Sprint ID | NEVER hardcode. Always `jira_get_sprints_from_board()`. Wrong sprint = silent failure |
| **HR8** Subtask alignment | Dates within parent range. SP sum reasonable vs parent. Misalignment → wrong capacity/burndown |
| **HR9** Desc alignment | Story ACs covered by subtask objectives. Epic scope in children. `/verify-issue --with-subtasks` (A1-A6) |
| **HR10** Subtask sprint | NEVER set `{{SPRINT_FIELD}}` on subtasks. Inherited from parent. API error + cascade failure |

## Context Management

**Compaction:** When context is compacted, ALWAYS preserve: (1) list of modified files + issue keys, (2) pending HR5/HR6 operations, (3) current phase of active skill workflow, (4) sprint IDs looked up this session. Hooks re-inject HR reminders automatically via `post-compact-reinject.py`.

**Subagents:** Use `.claude/agents/` for isolated investigation — keeps main context clean. Available: `code-explorer` (haiku), `issue-reader` (haiku), `jira-search` (haiku), `quality-gate` (haiku), `story-writer` (sonnet), `alignment-checker` (sonnet), `sprint-planner` (opus).

Run `/optimize-context` when CLAUDE.md feels outdated or context exceeds 15 KB.
