# QUICKSTART — atlassian-pm Plugin

Agile documentation system that automates Jira/Confluence workflows via Claude Code slash commands.

**Read time:** ~5 minutes

---

## Prerequisites

| Requirement | Install |
|-------------|---------|
| Claude Code CLI | [docs.anthropic.com](https://docs.anthropic.com/claude-code) |
| `acli` (Atlassian CLI) | `brew tap atlassian/homebrew-acli && brew install acli` |
| `uv` (Python package manager) | `brew install uv` |
| MCP server: `mcp-atlassian` | Provides Jira + Confluence tool access |
| Jira Cloud access | Project must exist with appropriate permissions |

After installing `acli`, authenticate once:

```bash
acli auth login
```

---

## Install

```bash
# Install the plugin
claude plugin install atlassian-pm@atlassian-pm

# Run first-time setup (interactive wizard)
# Installs Python deps, configures Jira project key, registers MCP server
/atlassian-pm:setup
```

---

## Verify Installation

```bash
/atlassian-pm:doctor
# Expected: 9-10 checks passed
```

If any check fails, the doctor output will tell you exactly what to fix.

---

## Core Skills (Slash Commands)

| Skill | When to use |
|-------|-------------|
| `/atlassian-pm:setup` | First-time setup — installs deps, configures Jira, registers MCP |
| `/atlassian-pm:doctor` | Health check — 10 checks, shows what's broken |
| `/atlassian-pm:story-full` | Create a User Story with subtasks (main PM workflow) |
| `/atlassian-pm:create-epic` | Create Epic + Confluence epic doc from product vision |
| `/atlassian-pm:analyze-story` | Analyze an existing story, create implementation subtasks |
| `/atlassian-pm:plan-sprint` | Sprint planning — capacity, carry-over, assignments |
| `/atlassian-pm:feature-blueprint` | Multi-agent feature design (5 domain experts + debate) |
| `/atlassian-pm:verify-issue` | Verify issue quality + alignment (A1-A6 checks) |
| `/atlassian-pm:sync-alignment` | Sync story-subtask descriptions + dates |
| `/atlassian-pm:update-story` | Update an existing User Story |
| `/atlassian-pm:update-subtask` | Update an existing Sub-task |
| `/atlassian-pm:update-epic` | Update an existing Epic |
| `/atlassian-pm:create-task` | Create a standalone Task |
| `/atlassian-pm:create-testplan` | Create Test Plan + QA subtask |
| `/atlassian-pm:create-doc` | Create Confluence page from template |
| `/atlassian-pm:update-doc` | Update an existing Confluence page |
| `/atlassian-pm:search-issues` | Search Jira issues with natural language |
| `/atlassian-pm:dependency-chain` | Map issue dependency chains |
| `/atlassian-pm:activity-report` | Sprint activity summary report |
| `/atlassian-pm:refine-feature` | Refine a feature with structured backlog |
| `/atlassian-pm:assign` | Quick-assign issue to team member (bypasses MCP bug) |
| `/atlassian-pm:atlassian-scripts` | Python scripts for complex Jira/Confluence ops |

---

## Common Workflows

### Workflow A: Create a new feature from scratch

```
1. /atlassian-pm:create-epic     → creates Epic + Confluence epic page
2. /atlassian-pm:story-full      → creates User Stories with subtasks under the epic
3. /atlassian-pm:plan-sprint     → assigns stories to sprint with capacity check
```

### Workflow B: Sprint planning

```
1. /atlassian-pm:plan-sprint     → enter sprint ID or let it auto-discover
                                   reviews capacity, carry-over, recommends assignments
                                   executes assignments on your approval
```

### Workflow C: Analyze and implement a story

```
1. /atlassian-pm:analyze-story {{PROJECT_KEY}}-XXX   → generates implementation subtasks
                                            review and approve the subtask plan
                                            subtasks created in Jira automatically
```

### Workflow D: Verify issue quality

```
1. /atlassian-pm:verify-issue {{PROJECT_KEY}}-XXX --with-subtasks
   flags: --fix (auto-repair), --dry-run (preview only)
```

---

## Quality Gate

Every Jira write is gated at **QG >= 90%**. Claude auto-scores ADF content before creating or updating any issue. If the score is below 90%, it auto-fixes and re-scores. You will see the score printed in the output before any write occurs.

You cannot bypass this gate — it is enforced by the HR1 hook.

---

## Background Agents

Skills invoke these automatically. Listed here for reference:

| Agent | Role | Model |
|-------|------|-------|
| `quality-gate` | Scores ADF content before writes | haiku |
| `code-explorer` | Maps codebase before creating subtasks | haiku |
| `issue-bootstrap` | Pre-fetches issue context efficiently | haiku |
| `issue-reader` | Reads issue details for downstream tasks | haiku |
| `jira-search` | Handles JQL search queries | haiku |
| `story-writer` | Writes ADF content for issues | sonnet |
| `alignment-checker` | Checks story-subtask alignment | sonnet |
| `sprint-planner` | Capacity + distribution analysis | sonnet |
| `pr-description-writer` | Generates PR description from branch + issue | haiku |
| `pr-review-jira-sync` | Syncs merged PR back to Jira | haiku |
| `backlog-groomer` | Readiness checks for sprint items | sonnet |
| `retrospective-analyst` | Sprint retro + Confluence page | sonnet |
| `velocity-tracker` | Tracks velocity history in config | haiku |
| `estimation-calibrator` | SP calibration from historical similarity | sonnet |
| `risk-forecaster` | 4-dimension delivery risk scoring per sprint | sonnet |
| `adf-surgeon` | Structural ADF repair for Jira quirks | haiku |
| `team-pattern-advisor` | Multi-sprint strategic pattern analysis | sonnet |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `acli not found` | `brew install acli` then `acli auth login` |
| MCP tools not found | Restart Claude Code after running `/atlassian-pm:setup` |
| QG keeps failing | Run `/atlassian-pm:verify-issue KEY --fix` |
| Stale issue data | Cache auto-invalidates after writes; force with `cache_invalidate(key)` |
| Subtask has wrong parent | Enforced by HR5: MCP create → verify parent → acli edit |
| Sprint ID mismatch | Never hardcode sprint IDs; always resolved via `jira_get_sprints_from_board()` |
| Reinstalled plugin, config gone | Run `/atlassian-pm:setup` — auto-restores `project-config.json` from `~/.config/atlassian/` backup |
| Reinstalled plugin, venv missing | Run `/atlassian-pm:setup` — detects missing venv, re-runs `uv sync` automatically |

Full troubleshooting reference: `skills/shared-references/troubleshooting.md`

---

## Enforced Rules (HR Rules)

These are enforced automatically by hooks — you cannot accidentally bypass them:

| Rule | Constraint |
|------|------------|
| HR1 | QG >= 90% required before any Jira write |
| HR3 | Assignee must be set via `acli` — MCP assignee silently fails |
| HR6 | Cache invalidated after every MCP write |
| HR7 | Sprint ID always looked up dynamically, never hardcoded |
| HR10 | Sprint field never set on subtasks (inherited from parent) |

Full rule definitions: `skills/shared-references/hr-rules.md`
