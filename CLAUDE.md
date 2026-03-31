# CLAUDE.md

## Overview

**Prefer retrieval-led reasoning:** search project docs (`references/`, qmd, `cache_get_issue`) and explore codebase before generating answers from training knowledge. When uncertain, retrieve first — don't guess.

Agile Documentation System — skills-based Jira/Confluence automation

**Plugin:** `atlassian-pm` · **Structure:** `SKILL.md` → phases → `references/` (25 docs) | `scripts/` (ai/, api/, lib/, sprint/, analysis/, docs/) | `mcp-servers/atlassian-cache/` (MCP) | `hooks/` (65 hooks in `plugin/` + `dev/`) | `agents/` (20) | `.claude/commands/` (13 orchestration chains)
**Skills layout:** 39 skills at `skills/{setup,epic,story,task,sprint,confluence,utilities}/<name>/SKILL.md` · shared refs at `../../../references/` from each skill · each skill has `## 🎓 Domain Expert Notes` (frameworks, metrics, failure modes)
**Vibe mode:** All creation skills default to **vibe mode** — fast, no ceremony, auto-generate. Use `--thorough` for full interview + ITERATE + REVIEW gates. Partial flags: `create-story --no-subtasks` (story only), `create-epic --no-doc` (Jira-only, skip Confluence), `vibe-plan --dry-run` (preview plan, no Jira write), `analyze-story --skip-explore` (skip codebase exploration), `bug-triage --no-assign` (skip assignment gate). Use `/vibe-plan` for idea → Epic + Stories + AI-Ready Subtasks in one shot.

**New here?** Start with [QUICKSTART.md](QUICKSTART.md) → then `/atlassian-pm:doctor` to verify setup.
**Skill index:** [skills/README.md](skills/README.md) — all 39 skills with phases, categories, and argument patterns.
**Hook reference:** [hooks/README.md](hooks/README.md) — all 65 hooks, what they enforce, and how to debug them.

## Project Settings

Core config (jira fields, team roster, services, environments): @.claude/project-config.json
Team detail (git evidence, capacity model, bus factor — load on-demand for release forecasting): `.claude/project-config-team-detail.json` _(gitignored — create from `.claude/project-config-team-detail.json.template`)_

**Dynamic lookup:** Board → `jira_get_agile_boards(project_key=<from config>)` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`

> **Config-first rule:** ALL project-specific values (project key, board ID, space key, team, services) live in `project-config.json` **only**. Never hardcode these values in skill files, agents, or hooks. Skill examples use `<project_key>` / `<space_key>` as placeholders — the actual values come from config at runtime. To switch projects or reconfigure, edit `project-config.json` — not the plugin.
**Prerequisites:** `acli` CLI, MCP (Jira + Confluence + Figma + GitHub), Python 3.x
**Git filters:** smudge/clean auto-convert placeholders↔real values · `./scripts/setup.sh` to configure
**Versioning:** `./scripts/bump-version.sh <X.Y.Z>` — updates marketplace.json + README badge, commits, tags, pushes, creates GitHub release, updates plugin + copies config in one step
**Plugin mode:** `claude --plugin-dir .` (dev) · Skills namespaced as `/atlassian-pm:<name>`

**Workflows:** [`skill-orchestration.md`](references/skill-orchestration.md) — how skills chain together · [`workflow-patterns.md`](references/workflow-patterns.md) — gate levels, QG scoring, annotation cycle
**Verify:** `/atlassian-pm:verify-issue` flags: `--with-subtasks` | `--fix` | `--dry-run`

**Tool selection:** `.claude/rules/tool-selection.md` · `.claude/rules/mermaid.md` · `.claude/rules/python-scripts.md` (3 auto-loaded rules) · `references/tools.md` (field presets)

## Common Mistakes

> Hook-enforced mistakes (HR2-HR10) are blocked automatically. Full troubleshooting: `references/troubleshooting.md`

| Category | Quick Fix |
| --- | --- |
| Hardcoding project/space key in skill files | WRONG — edit `.claude/project-config.json` instead; skills use `<project_key>`/`<space_key>` placeholders |
| Set parent on existing issue | MCP/acli silently fail → use `jira_set_parent.py --issues KEY --parent EPIC` |
| Sibling tool call errored | One parallel MCP call failed → all cancelled. Fix failing call first |
| Mermaid / Confluence issues | See `mermaid-guide.md` + `.claude/rules/mermaid.md` + `troubleshooting.md` |

## References

Loaded on demand from `references/` (25 docs, indexed by `templates.md`). **Scripts:** `skills/utilities/atlassian-scripts/SKILL.md` → `scripts/api/`

## Core Principles

| Principle | Rule |
| --- | --- |
| QG first | NEVER create/edit Atlassian issues before QG ≥ 90% |
| Phase order | Follow phases in order, never skip steps |
| Traceability | Everything links to parent: Sub-task→Story→Epic |
| Explore first | Prefer `Task(Explore)` before creating Sub-tasks (no explore = generic paths) |
| Vibe default | All creation skills default to fast mode (no ceremony). Use `--thorough` for full workflow. |

### HARD RULES (hooks enforce HR2–HR10 automatically)

Full definitions: `references/hr-rules.md`

| Rule | When | Action |
|------|------|--------|
| **HR1** QG ≥ 90% | Before any Jira write | `uv run scripts/api/validate_adf.py {file} --json` must score ≥ 90 |
| **HR2** JQL ORDER BY | `parent =` / `key in` JQL | NEVER add `ORDER BY` — parser error |
| **HR3** Assignee | Assign issue | `acli jira workitem assign -k "KEY" -a "email" -y` only — MCP silently fails |
| **HR4** Confluence macros | ToC/Children/Code blocks | `update_page_storage.py` only — MCP corrupts XML |
| **HR5** Subtask parent | Create subtask | MCP create → verify `parent.key` via `jira_get_issue` → acli edit if orphan |
| **HR6** Cache invalidate | Any MCP write | `cache_invalidate(issue_key)` after every write — use `auto_refresh=true` |
| **HR7** Sprint ID | Set `{{SPRINT_FIELD}}` | Never hardcode — `jira_get_sprints_from_board()` always |
| **HR8** Subtask dates | Create/update subtask | Dates within parent range · SP sum ≈ parent |
| **HR9** Desc alignment | Create/update any issue | Story ACs → subtask objectives · run `verify-issue --with-subtasks` |
| **HR10** Subtask sprint | Create subtask | NEVER set `{{SPRINT_FIELD}}` on subtasks — inherited from parent |

## Compact Instructions

When compacting, **preserve**: issue keys created/modified · pending HR5/HR6 ops · active skill phase · sprint IDs · QG scores.
**Discard**: verbose tool output · intermediate search results · exploration steps · full ADF bodies already written to Jira.

## Context Management

**Hooks:** `start_compact_reinject.py` (SessionStart/compact) + `post_compact_reinject.py` (PostCompact) re-inject HR rules + pending state after compaction.

**Agent invocation:** Skill phases that say `Agent(name: "X")` → use Agent tool with `subagent_type: "atlassian-pm:X"`. Mapping: `quality-gate`, `issue-bootstrap`, `story-writer`, etc.

**Subagents:** `agents/` for isolated investigation — full list: [references/agents.md](references/agents.md)

## Efficiency

- **No redundant reads:** Summarize `references/` on first read — never re-read same file.
- **Deliverable-first:** Every skill must produce its deliverable (ADF JSON, issue, report) within the session — don't stop at research phase.
- **Simple patterns:** Prefer `*.md` over complex globs. Default to simplest pattern that works.
- **Validate before commit:** Check frontmatter fields, `allowed-tools`, hook commands. Run markdownlint on `*.md` changes.
- **Parallel dispatch:** Use `> **🟢 PARALLEL**` blockquote in skill/agent phases to mark calls that can launch simultaneously — no dependency = single message, N Tool calls. Use `> **🟢 AUTO + PARALLEL**` when subagents are also auto-invoked.
