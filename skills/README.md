# Skills — atlassian-pm Plugin

33 skills implement multi-phase workflows for Jira/Confluence automation. Each skill is a Markdown instruction file that Claude follows step-by-step. Every skill includes a `## 🎓 Domain Expert Notes` section with industry frameworks (Scrum, SAFe, ITIL, DORA, IEEE 829), key metrics, expert decision criteria, and common failure modes.

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
| blueprint | `/atlassian-pm:blueprint` | 10 | atlassian-cache, mcp-atlassian | Multi-perspective blueprint via 5-role debate (PO, Domain Expert, Tech Lead, Engineer, QA). Outputs Confluence page (8 sections) + backlog map for downstream skills. Supports S/M/L tiers. |
| refine-epic | `/atlassian-pm:refine-epic` | 5 | atlassian-cache, mcp-atlassian | 4-role debate (PO, Tech Lead, Engineer, QA) for refining existing or draft stories. 2 rounds. Outputs refined stories ready for `/create-story`. |
| create-epic | `/atlassian-pm:create-epic` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Create Epic + Epic Doc from product vision. Includes RICE prioritization, VS planning, and blueprint handoff support. |
| update-epic | `/atlassian-pm:update-epic` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Update an existing Epic (scope, RICE, success metrics, format migration). Preserves intent; gates on scope changes. |
| plan-release | `/atlassian-pm:plan-release` | 9 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Multi-sprint release plan: velocity-based timeline, dependency mapping, Confluence release page, Jira Fix Version. |

### Story & Subtask

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| create-story | `/atlassian-pm:create-story` | 11 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | PO + TA combined workflow: creates User Story + Sub-tasks in one session. Includes codebase exploration, INVEST validation, QG, and blueprint handoff. |
| analyze-story | `/atlassian-pm:analyze-story` | 7 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | TA workflow for an existing story: parallel codebase exploration, sub-task design with TL decomposition ordering, QG, and Two-Step creation. |
| create-task | `/atlassian-pm:create-task` | 6 | atlassian-cache, mcp-atlassian, acli | Create a Jira Task with 4 type templates: tech-debt, bug, chore, spike. |
| create-testplan | `/atlassian-pm:create-testplan` | 6 | atlassian-cache, mcp-atlassian, acli | Create [QA] Sub-task with embedded Test Plan (Given/When/Then). 100% AC coverage required. |
| execute-testplan | `/atlassian-pm:execute-testplan` | 6 | mcp-atlassian, playwright | Execute test cases from a Google Sheet (linked via Jira Web links) using Playwright. Writes Pass/Fail/Skip results back to Sheet. Creates bug tickets with screenshot evidence for failures. |
| bug-triage | `/atlassian-pm:bug-triage` | 6 | atlassian-cache, mcp-atlassian, acli | QA triage workflow: intake → P1/P2/P3 severity scoring → duplicate check → assign → Jira Task creation. Distinct from `/create-task bug` (ticket only). |
| update-story | `/atlassian-pm:update-story` | 6 | atlassian-cache, mcp-atlassian, acli | Update an existing User Story (add/modify/remove AC, adjust scope). Validates subtask date alignment after changes. |
| update-subtask | `/atlassian-pm:update-subtask` | 6 | atlassian-cache, mcp-atlassian, acli | Update an existing Sub-task (format migration, add details, language fix, add AC). HR8 date alignment enforced. |
| update-task | `/atlassian-pm:update-task` | 6 | atlassian-cache, mcp-atlassian, acli | Update an existing Jira Task (migrate Wiki→ADF, add details, change type template). |
| assign-issue | `/atlassian-pm:assign-issue` | 1 | acli | Quick assign a Jira issue to a team member. Uses acli (HR3-safe). Supports unassign. |
| verify-issue | `/atlassian-pm:verify-issue` | 6 | atlassian-cache, mcp-atlassian, acli | Verify and improve issue quality: ADF format, INVEST, language, hierarchy alignment (A1–A6). Flags: `--with-subtasks`, `--fix`. |
| sync-artifacts | `/atlassian-pm:sync-artifacts` | 8 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Bidirectional sync from any artifact (Epic/Story/Sub-task/Confluence). Cascades changes across the full artifact graph. |
| spec-to-stories | `/atlassian-pm:spec-to-stories` | 8 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Convert Confluence spec page to Jira User Stories via spec-parser-agent. Dedup check, QG, batch create with HR5 verification. --dry-run supported. |

### Sprint Planning

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| plan-sprint | `/atlassian-pm:plan-sprint` | 8 | atlassian-cache, mcp-atlassian, acli | 8-phase sprint planning: capacity → carry-over → prioritize (Impact/Effort) → distribute (skill matrix + hours) → risk → execute assignments in Jira. |
| map-dependencies | `/atlassian-pm:map-dependencies` | 5 | atlassian-cache, mcp-atlassian | Sprint dependency analysis: dependency graph (Mermaid), critical path (CPM), swim lane plan per team member, decoupling strategies. |
| close-sprint | `/atlassian-pm:close-sprint` | 8 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Close sprint: triage incomplete issues, execute moves, close sprint, generate Confluence review page. Distinct from retrospective-analyst (analysis only). |
| standup-report | `/atlassian-pm:standup-report` | 4 | atlassian-cache, mcp-atlassian | Generate daily standup digest per assignee with anomaly detection (late starts, stale issues, overdue). Optional --post to Confluence. |
| reschedule-sprint | `/atlassian-pm:reschedule-sprint` | 5 | atlassian-cache, mcp-atlassian, acli | Bulk-shift issue dates across a sprint or issue list. Always previews before executing. HR8 alignment validated. |

### Confluence

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| create-doc | `/atlassian-pm:create-doc` | 4 | mcp-atlassian, mcp-confluence | Create Confluence page from template: tech-spec, ADR, or parent (category) page. |
| update-doc | `/atlassian-pm:update-doc` | 5 | mcp-confluence | Update an existing Confluence page: content, section, status, find/replace, or move. |

### Utilities

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| search-issues | `/atlassian-pm:search-issues` | 3 | atlassian-cache, mcp-atlassian | Search Jira via JQL + semantic similarity (cosine distance). Flags likely duplicates before creation. Runs on Haiku. |
| activity-report | `/atlassian-pm:activity-report` | 3 | claude-mem | **Plugin-internal meta-tool.** Tracks Claude Code session history via claude-mem. Not a PM workflow tool — use for plugin debugging/auditing only. |
| scan-tech-debt | `/atlassian-pm:scan-tech-debt` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence | Aggregate tech-debt/chore/spike issues into priority matrix dashboard on Confluence. Effort vs impact quadrant, trend tracking. |
| release-notes | `/atlassian-pm:release-notes` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence | Generate Confluence release notes from a Jira Fix Version. Groups issues by type (features/bugfixes/improvements). Supports `--dry-run`. |
| atlassian-scripts | `/atlassian-pm:atlassian-scripts` | — | — | Thin wrapper pointing to `scripts/api/`. Python scripts for Confluence/Jira REST API when MCP has limitations (macros, code blocks, parent fields). |
| status | `/atlassian-pm:status` | 4 | atlassian-cache, mcp-atlassian | Session navigator — active sprint status, team WIP, pending HR violations, and suggested next action. Use at session start or to resume after a break. |

---

## Compatibility Legend

The `x-compatibility` frontmatter field lists which external tools a skill depends on:

| Value | Meaning |
| --- | --- |
| `atlassian-cache` | Uses the atlassian-cache MCP (local SQLite cache + semantic search via sqlite-vec). Provides `cache_get_issue`, `cache_search`, `cache_similar_issues`. |
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
/atlassian-pm:create-story                            # interactive, no args
/atlassian-pm:create-story "admin monthly report"     # description as seed

/atlassian-pm:analyze-story {{PROJECT_KEY}}-123                   # issue key
/atlassian-pm:create-testplan {{PROJECT_KEY}}-123                 # issue key

/atlassian-pm:verify-issue {{PROJECT_KEY}}-123                    # single issue
/atlassian-pm:verify-issue {{PROJECT_KEY}}-123 --with-subtasks    # story + all subtasks
/atlassian-pm:verify-issue {{PROJECT_KEY}}-123 --with-subtasks --fix  # verify + auto-fix

/atlassian-pm:plan-sprint                             # next future sprint
/atlassian-pm:plan-sprint --sprint 456                # specific sprint ID
/atlassian-pm:plan-sprint --carry-over-only           # carry-over analysis only

/atlassian-pm:map-dependencies                        # current sprint
/atlassian-pm:map-dependencies --keys {{PROJECT_KEY}}-10,{{PROJECT_KEY}}-11  # specific issues

/atlassian-pm:search-issues "credit top-up"           # keyword search
/atlassian-pm:search-issues {{PROJECT_KEY}}-123 --children        # list subtasks
/atlassian-pm:search-issues --sprint current --assignee me

/atlassian-pm:assign-issue {{PROJECT_KEY}}-123 Kobi               # assign by name
/atlassian-pm:assign-issue {{PROJECT_KEY}}-123 unassign           # remove assignee

/atlassian-pm:activity-report                         # today
/atlassian-pm:activity-report --hours 48 --project {{COMPANY_LOWER}}-platform-api

/atlassian-pm:blueprint "real-time notifications"     # description
/atlassian-pm:blueprint {{PROJECT_KEY}}-456                       # from Jira epic

/atlassian-pm:close-sprint                            # close active sprint
/atlassian-pm:close-sprint --sprint 456               # specific sprint ID

/atlassian-pm:standup-report                          # today's active sprint
/atlassian-pm:standup-report --post                   # post to Confluence

/atlassian-pm:plan-release --name v2.3.0 --epics {{PROJECT_KEY}}-50,{{PROJECT_KEY}}-51  # with args
/atlassian-pm:plan-release                            # interactive

/atlassian-pm:reschedule-sprint --sprint 456 --shift +7         # shift sprint 7 days
/atlassian-pm:reschedule-sprint --issues {{PROJECT_KEY}}-123,{{PROJECT_KEY}}-124 --shift -3

/atlassian-pm:spec-to-stories 12345 --epic {{PROJECT_KEY}}-10     # page-id + epic
/atlassian-pm:spec-to-stories 12345 --dry-run         # preview only

/atlassian-pm:scan-tech-debt                          # create new radar
/atlassian-pm:scan-tech-debt --update                 # refresh existing page

/atlassian-pm:bug-triage                              # interactive full intake
/atlassian-pm:bug-triage "video upload fails iOS 17"  # summary pre-filled

/atlassian-pm:release-notes --version v2.3.0             # specific version
/atlassian-pm:release-notes --version v2.3.0 --dry-run  # preview
/atlassian-pm:release-notes                              # pick version interactively
```

---

## Shared References

`references/` (project root) contains 24 reference docs loaded on demand by skills. They are never loaded eagerly — each skill specifies which docs it needs.

| File | Purpose |
| --- | --- |
| `skill-orchestration.md` | How skills chain together; handoff patterns |
| `workflow-patterns.md` | Gate levels, QG scoring, annotation cycle, Parallel Explore, Two-Step subtask |
| `update-workflow.md` | Common patterns for all update-* skills: Phase 5 QG, Phase 6 apply, gate phrases, preserve intent |
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
| `hr-rules.md` | Full definitions for HR1–HR10 hard rules |
| `hooks-reference.md` | Hook enforcement details and event reference |
| `subtask-design-patterns.md` | Sub-task decomposition patterns, scope format, AC specificity |

---

## Creating or Modifying Skills

Skills are plain Markdown files. Follow existing conventions:

1. Create a subdirectory under the appropriate category folder (`skills/<category>/<name>/`). Categories: `setup/`, `epic/`, `story/`, `task/`, `sprint/`, `confluence/`, `utilities/`.
2. Write `SKILL.md` with YAML frontmatter + numbered phase instructions.
3. Use gate levels (`⛔ GATE`, `🟡 REVIEW`, `🔄 ITERATE`, `🟢 AUTO`) consistently.
4. Reference shared docs from `../../../references/` (three levels up to project root `references/`).
5. Validate frontmatter fields: `name`, `description`, `x-compatibility`, `argument-hint`.
6. Run `uv run dev-loop:skill-validator` if available to catch formatting issues.
