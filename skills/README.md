# Skills — atlassian-pm Plugin

30 skills implement multi-phase workflows for Jira/Confluence automation. Each skill is a Markdown instruction file that Claude follows step-by-step.

Invoke skills as slash commands: `/atlassian-pm:<name>` (or `/<name>` when running inside the plugin context).

---

## Skills by Category

### Setup & Health

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| setup | `/atlassian-pm:setup` | 6 (0–5) | Bash, acli, uv | First-time setup: installs deps, collects Jira config, authenticates acli, registers mcp-atlassian. Idempotent — safe to re-run. |
| doctor | `/atlassian-pm:doctor` | 1 (10 checks) | Bash | Health check: runs 10 checks (acli, uv, venv, MCP, config, board ID, git filters). Never stops on failure — shows complete picture. |

### Epic & Feature

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| feature-blueprint | `/atlassian-pm:feature-blueprint` | 10 | jira-cache-server, mcp-atlassian | Multi-perspective blueprint via 5-role debate (PO, Domain Expert, Tech Lead, Engineer, QA). Outputs Confluence page (8 sections) + backlog map for downstream skills. Supports S/M/L tiers. |
| refine-feature | `/atlassian-pm:refine-feature` | 5 | jira-cache-server, mcp-atlassian | 4-role debate (PO, Tech Lead, Engineer, QA) for refining existing or draft stories. 2 rounds. Outputs refined stories ready for `/story-full`. |
| create-epic | `/atlassian-pm:create-epic` | 6 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | Create Epic + Epic Doc from product vision. Includes RICE prioritization, VS planning, and blueprint handoff support. |
| update-epic | `/atlassian-pm:update-epic` | 6 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | Update an existing Epic (scope, RICE, success metrics, format migration). Preserves intent; gates on scope changes. |
| release-planner | `/atlassian-pm:release-planner` | 9 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | Multi-sprint release plan: velocity-based timeline, dependency mapping, Confluence release page, Jira Fix Version. |

### Story & Subtask

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| story-full | `/atlassian-pm:story-full` | 11 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | PO + TA combined workflow: creates User Story + Sub-tasks in one session. Includes codebase exploration, INVEST validation, QG, and blueprint handoff. |
| analyze-story | `/atlassian-pm:analyze-story` | 7 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | TA workflow for an existing story: parallel codebase exploration, sub-task design with TL decomposition ordering, QG, and Two-Step creation. |
| create-task | `/atlassian-pm:create-task` | 6 | jira-cache-server, mcp-atlassian, acli | Create a Jira Task with 4 type templates: tech-debt, bug, chore, spike. |
| create-testplan | `/atlassian-pm:create-testplan` | 6 | jira-cache-server, mcp-atlassian, acli | Create [QA] Sub-task with embedded Test Plan (Given/When/Then). 100% AC coverage required. |
| update-story | `/atlassian-pm:update-story` | 6 | jira-cache-server, mcp-atlassian, acli | Update an existing User Story (add/modify/remove AC, adjust scope). Validates subtask date alignment after changes. |
| update-subtask | `/atlassian-pm:update-subtask` | 6 | jira-cache-server, mcp-atlassian, acli | Update an existing Sub-task (format migration, add details, language fix, add AC). HR8 date alignment enforced. |
| update-task | `/atlassian-pm:update-task` | 6 | jira-cache-server, mcp-atlassian, acli | Update an existing Jira Task (migrate Wiki→ADF, add details, change type template). |
| assign | `/atlassian-pm:assign` | 1 | acli | Quick assign a Jira issue to a team member. Uses acli (HR3-safe). Supports unassign. |
| verify-issue | `/atlassian-pm:verify-issue` | 6 | jira-cache-server, mcp-atlassian, acli | Verify and improve issue quality: ADF format, INVEST, language, hierarchy alignment (A1–A6). Flags: `--with-subtasks`, `--fix`. |
| sync-alignment | `/atlassian-pm:sync-alignment` | 8 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | Bidirectional sync from any artifact (Epic/Story/Sub-task/Confluence). Cascades changes across the full artifact graph. |
| spec-to-stories | `/atlassian-pm:spec-to-stories` | 8 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | Convert Confluence spec page to Jira User Stories via spec-parser-agent. Dedup check, QG, batch create with HR5 verification. --dry-run supported. |

### Sprint Planning

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| plan-sprint | `/atlassian-pm:plan-sprint` | 8 | jira-cache-server, mcp-atlassian, acli | 8-phase sprint planning: capacity → carry-over → prioritize (Impact/Effort) → distribute (skill matrix + hours) → risk → execute assignments in Jira. |
| dependency-chain | `/atlassian-pm:dependency-chain` | 5 | jira-cache-server, mcp-atlassian | Sprint dependency analysis: dependency graph (Mermaid), critical path (CPM), swim lane plan per team member, decoupling strategies. |
| sprint-closer | `/atlassian-pm:sprint-closer` | 8 | jira-cache-server, mcp-atlassian, mcp-confluence, acli | Close sprint: triage incomplete issues, execute moves, close sprint, generate Confluence review page. Distinct from retrospective-analyst (analysis only). |
| standup-digest | `/atlassian-pm:standup-digest` | 4 | jira-cache-server, mcp-atlassian | Generate daily standup digest per assignee with anomaly detection (late starts, stale issues, overdue). Optional --post to Confluence. |
| bulk-reschedule | `/atlassian-pm:bulk-reschedule` | 5 | jira-cache-server, mcp-atlassian, acli | Bulk-shift issue dates across a sprint or issue list. Always previews before executing. HR8 alignment validated. |

### Confluence

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| create-doc | `/atlassian-pm:create-doc` | 4 | mcp-atlassian, mcp-confluence | Create Confluence page from template: tech-spec, ADR, or parent (category) page. |
| update-doc | `/atlassian-pm:update-doc` | 5 | mcp-confluence | Update an existing Confluence page: content, section, status, find/replace, or move. |

### Utilities

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| search-issues | `/atlassian-pm:search-issues` | 3 | jira-cache-server, mcp-atlassian | Search Jira via JQL + semantic similarity (cosine distance). Flags likely duplicates before creation. Runs on Haiku. |
| activity-report | `/atlassian-pm:activity-report` | 3 | claude-mem | Generate activity report from claude-mem history (sessions, observations, effort). Supports date ranges and project/type filters. Runs on Haiku. |
| tech-debt-radar | `/atlassian-pm:tech-debt-radar` | 6 | jira-cache-server, mcp-atlassian, mcp-confluence | Aggregate tech-debt/chore/spike issues into priority matrix dashboard on Confluence. Effort vs impact quadrant, trend tracking. |
| atlassian-scripts | — | — | — | Python script library for Confluence/Jira REST API operations. Not user-invocable directly; used internally by skills when MCP has limitations (macros, code blocks, parent fields). |

### Internal Only

| Skill | User-invocable | Description |
| --- | --- | --- |
| shared-references | No | 23 reference docs loaded on demand by skills. See section below. |

---

## Compatibility Legend

The `x-compatibility` frontmatter field lists which external tools a skill depends on:

| Value | Meaning |
| --- | --- |
| `jira-cache-server` | Uses the jira-cache-server MCP (local SQLite cache + semantic search via sqlite-vec). Provides `cache_get_issue`, `cache_search`, `cache_similar_issues`. |
| `mcp-atlassian` | Uses mcp-atlassian for Jira reads and writes (`jira_get_issue`, `jira_create_issue`, `jira_update_issue`, `jira_search`, etc.). |
| `mcp-confluence` | Uses mcp-atlassian's Confluence tools (`confluence_get_page`, `confluence_create_page`, `confluence_update_page`, `confluence_search`). |
| `acli` | Uses Atlassian CLI (`acli`) for operations where MCP silently fails: assignee (HR3), parent field on existing issues. |
| `claude-mem` | Uses claude-mem MCP for session memory and observation history. |

---

## Skill Anatomy

Every skill lives in its own subdirectory as `SKILL.md`. The file structure:

**YAML frontmatter** — parsed by Claude Code at load time:

| Field | Purpose |
| --- | --- |
| `name` | Skill identifier (matches directory name) |
| `description` | Shown in skill discovery; includes trigger phrases |
| `x-compatibility` | External tools required (see legend above) |
| `allowed-tools` | Restricts which Claude tools can be called (optional) |
| `argument-hint` | Shown as usage hint when the skill is invoked |
| `disable-model-invocation` | If `true`, Claude must follow instructions literally |
| `context: fork` | Runs in isolated context (does not pollute main session) |
| `model` | Override model for this skill (e.g., `haiku` for lightweight tasks) |
| `user-invocable: false` | Internal skill — not listed in user-facing discovery |

**Phase instructions** — numbered workflow steps after the frontmatter:

Each phase specifies actions, tool calls, and a gate level that controls how much Claude can auto-proceed:

| Gate | Symbol | Behavior |
| --- | --- | --- |
| AUTO | (none / `🟢 AUTO`) | Runs without asking; escalates only on failure |
| REVIEW | `🟡 REVIEW` | Presents result and proceeds unless user objects |
| ITERATE | `🔄 ITERATE` | Shows plan cards; loops until Approve/Annotate/Rework |
| GATE | `⛔ GATE` | Hard stop — waits for explicit user confirmation |

---

## Quick Reference — Argument Patterns

```
/atlassian-pm:story-full                              # interactive, no args
/atlassian-pm:story-full "admin monthly report"       # description as seed

/atlassian-pm:analyze-story BEP-123                   # issue key
/atlassian-pm:create-testplan BEP-123                 # issue key

/atlassian-pm:verify-issue BEP-123                    # single issue
/atlassian-pm:verify-issue BEP-123 --with-subtasks    # story + all subtasks
/atlassian-pm:verify-issue BEP-123 --with-subtasks --fix  # verify + auto-fix

/atlassian-pm:plan-sprint                             # next future sprint
/atlassian-pm:plan-sprint --sprint 456                # specific sprint ID
/atlassian-pm:plan-sprint --carry-over-only           # carry-over analysis only

/atlassian-pm:dependency-chain                        # current sprint
/atlassian-pm:dependency-chain --keys BEP-10,BEP-11  # specific issues

/atlassian-pm:search-issues "credit top-up"           # keyword search
/atlassian-pm:search-issues BEP-123 --children        # list subtasks
/atlassian-pm:search-issues --sprint current --assignee me

/atlassian-pm:assign BEP-123 Kobi                     # assign by name
/atlassian-pm:assign BEP-123 unassign                 # remove assignee

/atlassian-pm:activity-report                         # today
/atlassian-pm:activity-report --hours 48 --project tathep-platform-api

/atlassian-pm:feature-blueprint "real-time notifications"  # description
/atlassian-pm:feature-blueprint BEP-456               # from Jira epic

/atlassian-pm:sprint-closer                           # close active sprint
/atlassian-pm:sprint-closer --sprint 456              # specific sprint ID

/atlassian-pm:standup-digest                          # today's active sprint
/atlassian-pm:standup-digest --post                   # post to Confluence

/atlassian-pm:release-planner --name v2.3.0 --epics BEP-50,BEP-51  # with args
/atlassian-pm:release-planner                         # interactive

/atlassian-pm:bulk-reschedule --sprint 456 --shift +7           # shift sprint 7 days
/atlassian-pm:bulk-reschedule --issues BEP-123,BEP-124 --shift -3

/atlassian-pm:spec-to-stories 12345 --epic BEP-10     # page-id + epic
/atlassian-pm:spec-to-stories 12345 --dry-run         # preview only

/atlassian-pm:tech-debt-radar                         # create new radar
/atlassian-pm:tech-debt-radar --update                # refresh existing page
```

---

## Shared References

`skills/shared-references/` contains 23 reference docs loaded on demand by skills. They are never loaded eagerly — each skill specifies which docs it needs.

| File | Purpose |
| --- | --- |
| `skill-orchestration.md` | How skills chain together; handoff patterns |
| `workflow-patterns.md` | Gate levels, QG scoring, annotation cycle, Parallel Explore, Two-Step subtask |
| `team-capacity.md` | Capacity formulas, complexity-adjusted throughput, skill matrix thresholds |
| `sprint-frameworks.md` | RICE, Impact/Effort matrix, carry-over probability model, vertical slicing |
| `dependency-frameworks.md` | CPM algorithm, swim lane rules, decoupling patterns, risk scoring |
| `hr-rules.md` | Full definitions for HR1–HR10 (enforced by hooks) |
| `templates.md` | Index of ADF templates by issue type |
| `templates-core.md` | ADF CREATE/EDIT rules, panel types, inline code, styling |
| `templates-epic.md` | Epic ADF template |
| `templates-story.md` | Story ADF template |
| `templates-subtask.md` | Subtask ADF template + Two-Step workflow |
| `templates-task.md` | Task ADF templates (tech-debt, bug, chore, spike) |
| `templates-technote.md` | Technical Note best practices |
| `vertical-slice-guide.md` | VS patterns (skeleton, enabler, business rule splits), labels |
| `verification-checklist.md` | QG criteria by issue type (T1–T5, S1–S6, B1–B8) |
| `troubleshooting.md` | Common issues and fixes |
| `tools.md` | MCP vs acli decision rules, field presets, effort sizing |
| `writing-style.md` | Thai + transliteration conventions, concise scan-first format |
| `jql-quick-ref.md` | JQL patterns and filters |

---

## Creating or Modifying Skills

Skills are plain Markdown files. Follow existing conventions:

1. Create a subdirectory under `skills/` matching the skill name.
2. Write `SKILL.md` with YAML frontmatter + numbered phase instructions.
3. Use gate levels (`⛔ GATE`, `🟡 REVIEW`, `🔄 ITERATE`, `🟢 AUTO`) consistently.
4. Reference shared docs from `../shared-references/` rather than duplicating content.
5. Validate frontmatter fields: `name`, `description`, `x-compatibility`, `argument-hint`.
6. Run `uv run dev-loop:skill-validator` if available to catch formatting issues.
