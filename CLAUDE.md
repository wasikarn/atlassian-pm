# CLAUDE.md

## Overview

**Prefer retrieval-led reasoning:** search project docs (`references/`, qmd, `cache_get_issue`) and explore codebase before generating answers from training knowledge. When uncertain, retrieve first — don't guess.

Agile Documentation System — skills-based Jira/Confluence automation

**Plugin:** `atlassian-pm` · **Structure:** `SKILL.md` → phases → `references/` | `scripts/` (ai/, api/, lib/, sprint/) | `mcp-servers/atlassian-cache/` (MCP) | `hooks/` (77 hooks) | `agents/` (20) | `.claude/commands/` (13 chains)
**Skills:** 39 skills at `skills/{setup,epic,task,sprint,confluence,utilities}/<name>/SKILL.md` · shared refs at `../../../references/` · each has `## 🎓 Domain Expert Notes`
**Deprecated skills:** `skills/story/create-story/`, `skills/story/analyze-story/` — replaced by `/create-task` (feature mode)
**Issue hierarchy:** Epic → Task (2 levels only). No Story/Subtask — Task is the value unit with narrative + ACs + file paths.
**Templates:** No ADF panels — heading + paragraph + bulletList + table only. Thai headings (สรุปภาพรวม, เงื่อนไขที่ต้องผ่าน, etc.). Human-readable + AI-parseable.
**Vibe mode:** All creation skills default to **vibe mode** — fast, no ceremony, auto-generate. Use `--thorough` for full interview + ITERATE + REVIEW gates. Partial flags: `create-epic --no-doc` (Jira-only, skip Confluence), `vibe-plan --dry-run` (preview plan, no Jira write), `create-task --qa/--bug/--spike/--chore` (mode selection). Use `/vibe-plan` for idea → Epic + Tasks in one shot.

**New here?** Start with [QUICKSTART.md](QUICKSTART.md) → then `/atlassian-pm:doctor` to verify setup.
**Skill index:** [skills/README.md](skills/README.md) — all skills with phases, categories, and argument patterns.
**Hook reference:** [hooks/README.md](hooks/README.md) — all hooks, what they enforce, and how to debug them.

## Project Settings

Core config (jira fields, team roster, services, environments): @.claude/project-config.json
Team detail (git evidence, capacity model, bus factor — load on-demand for release forecasting): `.claude/project-config-team-detail.json` _(gitignored — create from `.claude/project-config-team-detail.json.template`)_

**Dynamic lookup:** Board → `jira_get_agile_boards(project_key=<from config>)` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`

> **Config-first rule:** ALL project-specific values (project key, board ID, space key, team, services) live in `project-config.json` **only**. Never hardcode these values in skill files, agents, or hooks. Skill examples use `<project_key>` / `<space_key>` as placeholders — the actual values come from config at runtime. To switch projects or reconfigure, edit `project-config.json` — not the plugin.
**Prerequisites:** `acli` CLI, MCP (Jira + Confluence + Figma + GitHub), Python 3.x
**Git filters:** smudge/clean auto-convert placeholders↔real values · `./scripts/setup.sh` to configure
**Versioning:** `./scripts/bump-version.sh <X.Y.Z>` — updates marketplace.json + README badge, commits, tags, pushes, creates GitHub release, refreshes marketplace cache in one step
**Plugin mode:** `claude --plugin-dir .` (dev) · Skills namespaced as `/atlassian-pm:<name>`
**MCP registration:** `atlassian-cache` registers via standalone `.mcp.json` at plugin root — do NOT add `mcpServers` to `plugin.json` (causes duplicate registration from cache dir without variable expansion)

**Workflows:** [`skill-orchestration.md`](references/skill-orchestration.md) — how skills chain together · [`workflow-patterns.md`](references/workflow-patterns.md) — gate levels, QG scoring, annotation cycle
**Verify:** `/atlassian-pm:verify-issue` flags: `--fix` | `--dry-run`
**Test:** `cd hooks && uv run pytest tests/ -q` · **Lint:** `markdownlint-cli2 "**/*.md"`

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
| Traceability | Everything links to parent: Task→Epic |
| Explore first | Prefer `Task(Explore)` before creating Tasks with file paths (no explore = generic paths) |
| Vibe default | All creation skills default to fast mode (no ceremony). Use `--thorough` for full workflow. |

### HARD RULES (hooks enforce HR2–HR10 automatically)

Full definitions: `references/hr-rules.md`

| Rule | When | Action |
|------|------|--------|
| **HR1** QG ≥ 90% | Before any Jira write | `uv run scripts/api/validate_adf.py {file} --json` must score ≥ 90 |
| **HR2** JQL ORDER BY | `parent =` / `key in` JQL | NEVER add `ORDER BY` — parser error |
| **HR3** Assignee | Assign issue | `acli jira workitem assign -k "KEY" -a "email" -y` only — MCP silently fails |
| **HR4** Confluence macros | ToC/Children/Code blocks | `update_page_storage.py` only — MCP corrupts XML |
| **HR5** Task parent | Create child Task | MCP create → verify `parent.key` via `jira_get_issue` → acli edit if orphan |
| **HR6** Cache invalidate | Any MCP write | `cache_invalidate(issue_key)` after every write — use `auto_refresh=true` |
| **HR7** Sprint ID | Set `{{SPRINT_FIELD}}` | Never hardcode — `jira_get_sprints_from_board()` always |
| **HR8** Task dates | Create/update child Task | Dates within parent range |
| **HR9** Desc alignment | Create/update any issue | Epic ACs → Task objectives · run `verify-issue` |
| **HR10** Task sprint | Create child Task under Epic | NEVER set `{{SPRINT_FIELD}}` on child Tasks — inherited from parent |

## Compact Instructions

When compacting, **preserve**: issue keys created/modified · pending HR5/HR6 ops · active skill phase · sprint IDs · QG scores.
**Discard**: verbose tool output · intermediate search results · exploration steps · full ADF bodies already written to Jira.

## Context Management

**Hooks:** `start_compact_reinject.py` (SessionStart/compact) + `post_compact_reinject.py` (PostCompact) re-inject HR rules + pending state after compaction.

**Agent invocation:** Skill phases that say `Agent(name: "X")` → use Agent tool with `subagent_type: "atlassian-pm:X"`. Mapping: `quality-gate`, `issue-bootstrap`, `estimation-calibrator`, etc.

**Subagents:** `agents/` for isolated investigation — full list: [references/agents.md](references/agents.md)

## Efficiency

- **No redundant reads:** Summarize `references/` on first read — never re-read same file.
- **Deliverable-first:** Every skill must produce its deliverable (ADF JSON, issue, report) within the session — don't stop at research phase.
- **Simple patterns:** Prefer `*.md` over complex globs. Default to simplest pattern that works.
- **Validate before commit:** Check frontmatter fields, `allowed-tools`, hook commands. Run markdownlint on `*.md` changes.
- **Parallel dispatch:** Use `> **🟢 PARALLEL**` blockquote in skill/agent phases to mark calls that can launch simultaneously — no dependency = single message, N Tool calls. Use `> **🟢 AUTO + PARALLEL**` when subagents are also auto-invoked.
