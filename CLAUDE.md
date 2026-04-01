# CLAUDE.md

## Overview

**Prefer retrieval-led reasoning:** search project docs (`references/`, qmd, `cache_get_issue`) and explore codebase before generating answers from training knowledge. When uncertain, retrieve first — don't guess.

Agile Documentation System — skills-based Jira/Confluence automation

**Plugin:** `atlassian-pm` · **Structure:** `SKILL.md` → phases → `references/` (26 docs) | `scripts/` (ai/, api/, lib/, sprint/) | `mcp-servers/atlassian-cache/` (MCP) | `hooks/` (61) | `agents/` (20) | `.claude/commands/` (13 chains)
**Skills:** 35 skills at `skills/{setup,epic,story,task,sprint,confluence,utilities}/<name>/SKILL.md` · shared refs at `../../../references/` · each has `## 🎓 Domain Expert Notes`
**Issue hierarchy:** Epic → Task (2 levels). Task carries narrative + ACs + file paths.
**Templates:** No ADF panels — heading + paragraph + bulletList + table only. Thai headings. Human-readable + AI-parseable.
**Data flow:** Skill phase → generate ADF JSON → `validate_adf.py` (QG ≥ 90%) → `acli --from-json` (create) or MCP `jira_update_issue` (update) → `cache_invalidate`

**New here?** Start with [QUICKSTART.md](QUICKSTART.md) → then `/atlassian-pm:doctor` to verify setup.
**Skill index:** [skills/README.md](skills/README.md) — all skills with phases, categories, and argument patterns.
**Hook reference:** [hooks/README.md](hooks/README.md) — all hooks, what they enforce, and how to debug them.

## Commands

| Command | Purpose |
| --- | --- |
| `./scripts/setup.sh` | First-time setup (git filters, config) |
| `./scripts/bump-version.sh <X.Y.Z>` | Version bump → commit → tag → push → GitHub release → marketplace refresh |
| `uv run scripts/api/validate_adf.py {file} --type task --json` | QG scoring (≥ 90 = pass) |
| `uv run scripts/api/validate_adf.py {file} --fix` | Auto-fix ADF issues |
| `acli jira workitem create --from-json {file}` | Create issue from ADF JSON |
| `acli jira workitem edit --from-json {file} --yes` | Update issue description from ADF JSON |
| `acli jira workitem assign -k "KEY" -a "email" -y` | Assign (HR3 — MCP silently fails) |
| `uv run scripts/api/jira_set_parent.py --issues KEY --parent EPIC` | Set parent (MCP/acli silently fail) |
| `cd hooks && uv run pytest tests/ -q` | Run hook tests |
| `markdownlint-cli2 "**/*.md"` | Lint markdown |
| `claude --plugin-dir .` | Dev mode (skills namespaced as `/atlassian-pm:<name>`) |

## Project Settings

Core config: `.claude/project-config.json` (jira fields, team, services, environments) — ALL project-specific values live here only. Never hardcode in skills/agents/hooks.
Team detail: `.claude/project-config-team-detail.json` _(gitignored — create from template)_
**Dynamic lookup:** Board → `jira_get_agile_boards(project_key=<from config>)` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`
**Prerequisites:** `acli` CLI, MCP (Jira + Confluence), Python 3.x · **MCP:** `atlassian-cache` via `.mcp.json` — never add to `plugin.json`

## create-task Modes

| Mode | Flag | Auto-detect keywords | Thai headings |
| --- | --- | --- | --- |
| feature | *(default)* | — | สิ่งที่ผู้ใช้ต้องการ · เงื่อนไขที่ต้องผ่าน · ขอบเขตไฟล์ · คำแนะนำการพัฒนา |
| qa | `--qa` | test, QA, ทดสอบ | วัตถุประสงค์ทดสอบ · ชุดทดสอบ |
| bug | `--bug` | bug, error, พัง | รายละเอียดปัญหา · ขั้นตอนทำซ้ำ · คาดหวัง vs เกิดจริง · เงื่อนไขที่ต้องผ่าน |
| spike | `--spike` | research, วิจัย, spike | คำถามวิจัย · บริบท · พื้นที่สำรวจ |
| chore | `--chore` | chore, upgrade, config | วัตถุประสงค์ · รายการงาน · เงื่อนไขที่ต้องผ่าน |

**Epic headings:** สรุปภาพรวม · คุณค่าทางธุรกิจ · ลูกค้าเห็นอะไร? · ขอบเขตงาน · เงื่อนไขที่ต้องผ่าน · ความเสี่ยงและวิธีรับมือ
**Vibe mode:** All creation skills default to fast mode. Use `--thorough` for full workflow. Use `/vibe-plan` for idea → Epic + Tasks in one shot.

## Common Mistakes

> Hook-enforced mistakes (HR2-HR7, HR9) are blocked automatically. Full troubleshooting: `references/troubleshooting.md`

| Mistake | Fix |
| --- | --- |
| Hardcoding project/space key | Edit `.claude/project-config.json` — skills use `<project_key>` placeholders |
| Set parent on existing issue | `jira_set_parent.py --issues KEY --parent EPIC` (MCP/acli silently fail) |
| Sibling tool call errored | One parallel MCP call failed → all cancelled. Fix failing call first |
| Using ADF panel nodes | Panels render as gray blockquote — use heading + text only (v3.0.0) |
| Mermaid / Confluence macros | `update_page_storage.py` — MCP corrupts XML. See `.claude/rules/mermaid.md` |
| MCP assignee field | MCP silently fails — use `acli jira workitem assign` only (HR3) |

## References

`references/` (26 docs, indexed by `templates.md`): ADF templates (`templates-core/epic/task.md`) · workflow (`workflow-patterns.md`, `skill-orchestration.md`, `hr-rules.md`) · guides (`writing-style.md`, `tools.md`, `troubleshooting.md`) · scripts via `skills/utilities/atlassian-scripts/SKILL.md`
**Auto-loaded rules:** `.claude/rules/tool-selection.md` · `.claude/rules/mermaid.md` · `.claude/rules/python-scripts.md`

## Core Principles

| Principle | Rule |
| --- | --- |
| QG first | NEVER create/edit Atlassian issues before QG ≥ 90% |
| Phase order | Follow phases in order, never skip steps |
| Traceability | Everything links to parent: Task→Epic |
| Explore first | Prefer `Task(Explore)` before creating Tasks with file paths |
| Vibe default | Fast mode default. `--thorough` for full workflow |

### HARD RULES (hooks enforce HR2–HR7, HR9 automatically)

Full definitions: `references/hr-rules.md`

| Rule | When | Action |
| --- | --- | --- |
| **HR1** QG ≥ 90% | Before any Jira write | `validate_adf.py {file} --json` must score ≥ 90 |
| **HR2** JQL ORDER BY | `parent =` / `key in` JQL | NEVER add `ORDER BY` — parser error |
| **HR3** Assignee | Assign issue | `acli assign` only — MCP silently fails |
| **HR4** Confluence macros | ToC/Children/Code blocks | `update_page_storage.py` only — MCP corrupts XML |
| **HR5** Task parent | Create child Task | MCP create → verify `parent.key` → acli edit if orphan |
| **HR6** Cache invalidate | Any MCP write | `cache_invalidate(issue_key)` after every write |
| **HR7** Sprint ID | Set `{{SPRINT_FIELD}}` | Never hardcode — `jira_get_sprints_from_board()` always |
| **HR9** Desc alignment | Create/update any issue | Epic ACs → Task objectives · run `verify-issue` |

## Context Management

| Mechanism | Details |
| --- | --- |
| Compaction preserve | Issue keys · pending HR5/HR6 ops · active phase · sprint IDs · QG scores |
| Compaction discard | Verbose tool output · search results · exploration steps · ADF bodies written |
| Hooks | `start_compact_reinject.py` + `post_compact_reinject.py` re-inject HR rules + pending state |
| Agent invocation | `Agent(name: "X")` in skill → `subagent_type: "atlassian-pm:X"` |
| Subagents | `agents/` (20) — full list: `references/agents.md` |

## Efficiency

| Rule | Why |
| --- | --- |
| No redundant reads | Summarize `references/` on first read — never re-read same file |
| Deliverable-first | Every skill must produce its deliverable within the session |
| Simple patterns | Prefer `*.md` over complex globs |
| Validate before commit | Check frontmatter, `allowed-tools`, hooks. Run markdownlint |
| Parallel dispatch | `> **🟢 PARALLEL**` in skill phases = single message, N tool calls |
