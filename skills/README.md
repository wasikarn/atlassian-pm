# Skills — atlassian-pm Plugin

35 skills implement multi-phase workflows for Jira/Confluence automation. Each skill is a Markdown instruction file that Claude follows step-by-step. Every skill includes a `## 🎓 Domain Expert Notes` section with industry frameworks (Scrum, SAFe, ITIL, DORA, IEEE 829), key metrics, expert decision criteria, and common failure modes.

Invoke skills as slash commands: `/atlassian-pm:<name>` (or `/<name>` when running inside the plugin context).

## Skills by Category

### Setup & Health

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| atlassian-setup | `/atlassian-pm:apm-setup` | 6 (0–5) | Bash, acli, uv | First-time setup: installs deps, collects Jira config, authenticates acli, registers mcp-atlassian. Idempotent — safe to re-run. |
| atlassian-doctor | `/atlassian-pm:apm-doctor` | 1 (10 checks) | Bash | Health check: runs 10 checks (acli, uv, venv, MCP, config, board ID, git filters). Never stops on failure — shows complete picture. |

### Epic & Feature

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| blueprint | `/atlassian-pm:apm-blueprint` | 10 | atlassian-cache, mcp-atlassian | Multi-perspective blueprint via 5-role debate (PO, Domain Expert, Tech Lead, Engineer, QA). Outputs Confluence page (8 sections) + backlog map for downstream skills. Supports S/M/L tiers. |
| refine-epic | `/atlassian-pm:apm-refine-epic` | 5 | atlassian-cache, mcp-atlassian | 4-role debate (PO, Tech Lead, Engineer, QA) for refining existing or draft stories. 2 rounds. Outputs refined stories ready for `/create-story`. |
| create-epic | `/atlassian-pm:apm-create-epic` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Create Epic + Epic Doc from product vision. Vibe mode (default): auto-extract, skip RICE+ITERATE. `--thorough` for full interview + RICE + annotation rounds. |
| vibe-plan | `/atlassian-pm:apm-vibe-plan` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Idea → Epic + Stories + AI-Ready Subtasks in one shot. Max 2 user interactions. Each subtask includes Implementation Hints (entry point, pattern, test command) for Claude Code execution. |
| update-epic | `/atlassian-pm:apm-update-epic` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Update an existing Epic (scope, RICE, success metrics, format migration). Preserves intent; gates on scope changes. |
| plan-release | `/atlassian-pm:apm-plan-release` | 9 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Multi-sprint release plan: velocity-based timeline, dependency mapping, Confluence release page, Jira Fix Version. |
| epic-health | `/atlassian-pm:apm-epic-health` | 4 | atlassian-cache, mcp-atlassian | Epic health audit: story coverage, SP totals vs velocity, timeline feasibility, AC alignment, and missing QG verifications. |

### Task

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| create-task | `/atlassian-pm:apm-create-task` | 5 | atlassian-cache, mcp-atlassian, acli | Create a Jira Task with 4 type templates: tech-debt, bug, chore, spike. Vibe mode (default): auto-detect type, skip review gate. |
| create-testplan | `/atlassian-pm:apm-create-testplan` | 6 | atlassian-cache, mcp-atlassian, acli | Create [QA] Sub-task with embedded Test Plan (Given/When/Then). 100% AC coverage required. |
| execute-testplan | `/atlassian-pm:apm-execute-testplan` | 6 | mcp-atlassian, playwright | Execute test cases from a Google Sheet (linked via Jira Web links) using Playwright. Writes Pass/Fail/Skip results back to Sheet. Creates bug tickets with screenshot evidence for failures. |
| bug-triage | `/atlassian-pm:apm-bug-triage` | 6 | atlassian-cache, mcp-atlassian, acli | QA triage workflow: intake → P1/P2/P3 severity scoring → duplicate check → assign → Jira Task creation. Distinct from `/create-task bug` (ticket only). |
| update-task | `/atlassian-pm:apm-update-task` | 6 | atlassian-cache, mcp-atlassian, acli | Update an existing Jira Task (migrate Wiki→ADF, add details, change type template). |
| assign-issue | `/atlassian-pm:apm-assign-issue` | 1 | acli | Quick assign a Jira issue to a team member. Uses acli (HR3-safe). Supports unassign. |
| verify-issue | `/atlassian-pm:apm-verify-issue` | 6 | atlassian-cache, mcp-atlassian, acli | Verify and improve issue quality: ADF format, INVEST, language, hierarchy alignment (A1–A6). Flags: `--with-subtasks`, `--fix`. |
| sync-artifacts | `/atlassian-pm:apm-sync-artifacts` | 8 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Bidirectional sync from any artifact (Epic/Story/Sub-task/Confluence). Cascades changes across the full artifact graph. |
| spec-to-stories | `/atlassian-pm:apm-spec-to-stories` | 8 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Convert Confluence spec page to Jira User Stories via spec-parser-agent. Dedup check, QG, batch create with HR5 verification. --dry-run supported. |

### DLC Workflow

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| start-ticket | `/atlassian-pm:apm-start-ticket` | 5 | mcp-atlassian, atlassian-cache | Read ticket AC + transition to In Progress in one command. Tiered guard: warn on In Progress/Reopened, block on Done. WIP gate enforced. |
| ship-to-qa | `/atlassian-pm:apm-ship-to-qa` | 7 | mcp-atlassian, atlassian-cache, Bash (gh) | Post PR + CF Pages preview URLs to Jira comment + transition to Ready for QA. Auto-detects PR from current branch. WIP gate enforced. |

### Flow & Release

> **Scrumban:** No sprint planning ceremony — work flows via pull/replenishment (`/flow-check`). Skills below support flow health, release forecasting, and sprint close.

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| flow-check | `/atlassian-pm:apm-flow-check` | 3 | atlassian-cache, mcp-atlassian | Board health snapshot + Scrumban replenishment trigger. Primary Scrumban flow tool. |
| map-dependencies | `/atlassian-pm:apm-map-dependencies` | 5 | atlassian-cache, mcp-atlassian | Dependency graph (Mermaid), critical path (CPM), swim lane per team member, decoupling strategies. |
| close-sprint | `/atlassian-pm:apm-close-sprint` | 8 | atlassian-cache, mcp-atlassian, mcp-confluence, acli | Close sprint: triage incomplete issues, execute moves, close sprint, generate Confluence review page. |
| standup-report | `/atlassian-pm:apm-standup-report` | 4 | atlassian-cache, mcp-atlassian | Daily standup digest per assignee with anomaly detection (late starts, stale issues, overdue). Optional --post to Confluence. |
| retro-actions | `/atlassian-pm:apm-retro-actions` | 5 | atlassian-cache, mcp-atlassian, acli | Parse action-items block from a retrospective (Confluence page or session context) → create one Jira task per action item with sprint assignment. Use after `close-sprint` or `retrospective-analyst`. |
| reschedule-sprint | `/atlassian-pm:apm-reschedule-sprint` | 5 | atlassian-cache, mcp-atlassian, acli | Bulk-shift issue dates across a sprint or issue list. Always previews before executing. HR8 alignment validated. |
| plan-sprint | `/atlassian-pm:apm-plan-sprint` | 8 | atlassian-cache, mcp-atlassian, acli | _(Release forecasting only)_ Capacity-based sprint allocation for release planning context. Not used in Scrumban daily flow. |

### Confluence

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| create-doc | `/atlassian-pm:apm-create-doc` | 4 | mcp-atlassian, mcp-confluence | Create Confluence page from template: tech-spec, ADR, or parent (category) page. |
| update-doc | `/atlassian-pm:apm-update-doc` | 5 | mcp-confluence | Update an existing Confluence page: content, section, status, find/replace, or move. |

### Utilities

| Skill | Command | Phases | Requires | Description |
| --- | --- | --- | --- | --- |
| search-issues | `/atlassian-pm:apm-search-issues` | 3 | atlassian-cache, mcp-atlassian | Search Jira via JQL + semantic similarity (cosine distance). Flags likely duplicates before creation. Runs on Haiku. |
| activity-report | `/atlassian-pm:apm-activity-report` | 3 | claude-mem | **Plugin-internal meta-tool.** Tracks Claude Code session history via claude-mem. Not a PM workflow tool — use for plugin debugging/auditing only. |
| scan-tech-debt | `/atlassian-pm:apm-scan-tech-debt` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence | Aggregate tech-debt/chore/spike issues into priority matrix dashboard on Confluence. Effort vs impact quadrant, trend tracking. |
| release-notes | `/atlassian-pm:apm-release-notes` | 6 | atlassian-cache, mcp-atlassian, mcp-confluence | Generate Confluence release notes from a Jira Fix Version. Groups issues by type (features/bugfixes/improvements). Supports `--dry-run`. |
| atlassian-scripts | `/atlassian-pm:atlassian-scripts` | — | — | Thin wrapper pointing to `scripts/api/`. Python scripts for Confluence/Jira REST API when MCP has limitations (macros, code blocks, parent fields). |
| status | `/atlassian-pm:apm-status` | 4 | atlassian-cache, mcp-atlassian | Session navigator — active sprint status, team WIP, pending HR violations, and suggested next action. Use at session start or to resume after a break. |

## Compatibility Legend

| Value | Meaning |
| --- | --- |
| `atlassian-cache` | Uses the atlassian-cache MCP (local SQLite cache + semantic search via sqlite-vec). Provides `cache_get_issue`, `cache_search`, `cache_similar_issues`. |
| `mcp-atlassian` | Uses mcp-atlassian for Jira reads and writes (`jira_get_issue`, `jira_create_issue`, `jira_update_issue`, `jira_search`, etc.). |
| `mcp-confluence` | Uses mcp-atlassian's Confluence tools (`confluence_get_page`, `confluence_create_page`, `confluence_update_page`, `confluence_search`). |
| `acli` | Uses Atlassian CLI (`acli`) for operations where MCP silently fails: assignee (HR3), parent field on existing issues. |
| `claude-mem` | Uses claude-mem MCP for session memory and observation history. |

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
| `context: fork` | Runs in isolated context (does not pollute main session) |
| `model` | Override model for this skill (e.g., `haiku` for lightweight tasks) |
| `user-invocable: false` | Internal skill — hidden from `/` menu but Claude can still auto-trigger |

**Phase instructions** — numbered workflow steps after the frontmatter:

Each phase specifies actions, tool calls, and a gate level that controls how much Claude can auto-proceed:

| Gate | Symbol | Behavior |
| --- | --- | --- |
| AUTO | (none / `🟢 AUTO`) | Runs without asking; escalates only on failure |
| REVIEW | `🟡 REVIEW` | Presents result and proceeds unless user objects |
| ITERATE | `🔄 ITERATE` | Shows plan cards; loops until Approve/Annotate/Rework |
| GATE | `⛔ GATE` | Hard stop — waits for explicit user confirmation |

## Quick Reference — Argument Patterns

```text
/atlassian-pm:apm-create-task                             # interactive, no args
/atlassian-pm:apm-create-task "admin monthly report"      # description as seed

/atlassian-pm:apm-verify-issue {{PROJECT_KEY}}-123                    # issue key
/atlassian-pm:apm-create-testplan {{PROJECT_KEY}}-123                 # issue key

/atlassian-pm:apm-verify-issue {{PROJECT_KEY}}-123                    # single issue
/atlassian-pm:apm-verify-issue {{PROJECT_KEY}}-123 --with-subtasks    # story + all subtasks
/atlassian-pm:apm-verify-issue {{PROJECT_KEY}}-123 --with-subtasks --fix  # verify + auto-fix

/atlassian-pm:apm-flow-check                              # board health + WIP status
/atlassian-pm:apm-flow-check --replenish                  # replenish Ready queue only

/atlassian-pm:apm-map-dependencies                        # dependency graph for current issues
/atlassian-pm:apm-map-dependencies --keys {{PROJECT_KEY}}-10,{{PROJECT_KEY}}-11  # specific issues

# (release forecasting only — not Scrumban daily flow)
/atlassian-pm:apm-plan-sprint                             # capacity-based sprint allocation
/atlassian-pm:apm-plan-sprint --sprint 456                # specific sprint ID

/atlassian-pm:apm-search-issues "credit top-up"           # keyword search
/atlassian-pm:apm-search-issues {{PROJECT_KEY}}-123 --children        # list subtasks
/atlassian-pm:apm-search-issues --sprint current --assignee me

/atlassian-pm:apm-assign-issue {{PROJECT_KEY}}-123 Kobi               # assign by name
/atlassian-pm:apm-assign-issue {{PROJECT_KEY}}-123 unassign           # remove assignee

/atlassian-pm:apm-activity-report                         # today
/atlassian-pm:apm-activity-report --hours 48 --project {{COMPANY_LOWER}}-platform-api

/atlassian-pm:apm-blueprint "real-time notifications"     # description
/atlassian-pm:apm-blueprint {{PROJECT_KEY}}-456                       # from Jira epic

/atlassian-pm:apm-close-sprint                            # close active sprint
/atlassian-pm:apm-close-sprint --sprint 456               # specific sprint ID

/atlassian-pm:apm-retro-actions                           # parse retro from session context
/atlassian-pm:apm-retro-actions --from-page 12345         # from Confluence page
/atlassian-pm:apm-retro-actions --sprint 456 --dry-run    # preview tasks only

/atlassian-pm:apm-epic-health {{PROJECT_KEY}}-50                       # audit specific epic
/atlassian-pm:apm-epic-health                             # audit all active epics

/atlassian-pm:apm-standup-report                          # today's active sprint
/atlassian-pm:apm-standup-report --post                   # post to Confluence

/atlassian-pm:apm-plan-release --name v2.3.0 --epics {{PROJECT_KEY}}-50,{{PROJECT_KEY}}-51  # with args
/atlassian-pm:apm-plan-release                            # interactive

/atlassian-pm:apm-reschedule-sprint --sprint 456 --shift +7         # shift sprint 7 days
/atlassian-pm:apm-reschedule-sprint --issues {{PROJECT_KEY}}-123,{{PROJECT_KEY}}-124 --shift -3

/atlassian-pm:apm-spec-to-stories 12345 --epic {{PROJECT_KEY}}-10     # page-id + epic
/atlassian-pm:apm-spec-to-stories 12345 --dry-run         # preview only

/atlassian-pm:apm-scan-tech-debt                          # create new radar
/atlassian-pm:apm-scan-tech-debt --update                 # refresh existing page

/atlassian-pm:apm-bug-triage                              # interactive full intake
/atlassian-pm:apm-bug-triage "video upload fails iOS 17"  # summary pre-filled

/atlassian-pm:apm-release-notes --version v2.3.0             # specific version
/atlassian-pm:apm-release-notes --version v2.3.0 --dry-run  # preview
/atlassian-pm:apm-release-notes                              # pick version interactively

/atlassian-pm:apm-start-ticket {{PROJECT_KEY}}-123                       # read AC + transition In Progress
/atlassian-pm:apm-start-ticket {{PROJECT_KEY}}-123 --force               # override Done/Closed guard
/atlassian-pm:apm-ship-to-qa {{PROJECT_KEY}}-123                         # post PR + preview URLs + transition QA
```

## Shared References

`references/` (project root) contains 24 reference docs loaded on demand by skills. Each skill specifies which docs it needs.

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
| `templates-task.md` | Task ADF templates (tech-debt, bug, chore, spike) |
| `templates-technote.md` | Technical Note best practices |
| `vertical-slice-guide.md` | VS patterns (skeleton, enabler, business rule splits), labels |
| `verification-checklist.md` | QG criteria by issue type (T1–T5, S1–S6, B1–B8) |
| `troubleshooting.md` | Common issues and fixes |
| `tools.md` | MCP vs acli decision rules, field presets, effort sizing |
| `writing-style.md` | Thai + transliteration conventions, concise scan-first format |
| `jql-quick-ref.md` | JQL patterns and filters |
| `hooks-reference.md` | Hook enforcement details and event reference |
| `subtask-design-patterns.md` | Sub-task decomposition patterns, scope format, AC specificity |
| `agents.md` | All subagents: model, tier, and usage context |

## Creating or Modifying Skills

Skills are plain Markdown files. Follow existing conventions:

1. Create a subdirectory under the appropriate category folder (`skills/<category>/<name>/`). Categories: `setup/`, `epic/`, `story/`, `task/`, `sprint/`, `confluence/`, `utilities/`.
2. Write `SKILL.md` with YAML frontmatter + numbered phase instructions.
3. Use gate levels (`⛔ GATE`, `🟡 REVIEW`, `🔄 ITERATE`, `🟢 AUTO`) consistently.
4. Reference shared docs from `../../../references/` (three levels up to project root `references/`).
5. Validate frontmatter fields: `name`, `description`, `x-compatibility`, `argument-hint`.
6. Run `uv run dev-loop:skill-validator` if available to catch formatting issues.
