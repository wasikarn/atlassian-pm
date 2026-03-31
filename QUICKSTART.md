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

---

## Install

### Claude Desktop (GUI)

Open **Settings → Extensions → Add marketplace**, enter `wasikarn/atlassian-pm`, then click **Install**.

### Claude Code (CLI)

```bash
# 1. Add marketplace
/plugin marketplace add wasikarn/atlassian-pm

# 2. Install plugin
/plugin install atlassian-pm@atlassian-pm

# 3. Run setup — asks for site, project key, board ID
/atlassian-pm:setup
```

Setup configures: acli auth · mcp-atlassian MCP server · `~/.config/atlassian/.env` · git smudge/clean filters · atlassian-cache venv (deps)

The `atlassian-cache` MCP server starts **automatically** when the plugin loads — no manual registration needed. Setup only installs the Python venv that the server depends on.

> Claude Code must be **restarted once** after setup to activate the MCP server.

### Optional: Board Monitor Daemon

Runs `board_monitor.py` in the background, auto-starts on login, and feeds proactive Jira insights into AI context:

```bash
# Install once — auto-starts on login
CLAUDE_PLUGIN_ROOT=<path-to-plugin> CLAUDE_PROJECT_DIR=<path-to-project> \
  scripts/setup_monitor.sh

# Uninstall
scripts/teardown_monitor.sh
```

`/atlassian-pm:doctor` reports daemon status — run it to confirm.

---

## Verify Installation

```bash
/atlassian-pm:doctor
# Expected: 9-12 checks passed (12 if board_monitor daemon is running)
```

If any check fails, the doctor output will tell you exactly what to fix.

---

## Commands (Fast-Path Chains)

End-to-end chains — the fastest way to get things done. Invoked as `/name` (no namespace prefix).

| Command | Description |
|---------|-------------|
| `/vibe-full` | 🚀 Idea → AI-Ready tasks in one shot (dedup → vibe-plan → verify) |
| `/story-full` | Dedup check → create story + subtasks → verify |
| `/epic-full` | Dedup → create epic → create story → verify |
| `/blueprint-full` | Greenfield design → epic → story → verify |
| `/bug-full` | Dedup → bug triage → test plan |
| `/qa-full` | Create test plan → run against staging |
| `/story-analyze-full` | Analyze story → verify alignment |
| `/sprint-close-full` | Close sprint → retrospective |
| `/sprint-plan-full` | Capacity planning → map dependencies |
| `/release-full` | Release plan → Confluence release notes |
| `/tech-debt-full` | Scan tech debt → create tasks |

---

## Core Skills (Slash Commands)

| Skill | When to use |
|-------|-------------|
| `/atlassian-pm:setup` | First-time setup — installs deps, configures Jira, registers MCP |
| `/atlassian-pm:doctor` | Health check — 10 checks, shows what's broken |
| **Backlog** | |
| `/atlassian-pm:vibe-plan` | 🚀 Idea → Epic + Stories + AI-Ready Subtasks (max 2 interactions). `--dry-run` to preview plan without creating in Jira. |
| `/atlassian-pm:blueprint` | Multi-role feature design (5 domain experts + debate) |
| `/atlassian-pm:refine-epic` | 4-role debate for unclear or high-risk requirements |
| `/atlassian-pm:create-epic` | Epic + Confluence doc. `--no-doc` for Jira-only (skip Confluence). `--thorough` for RICE + annotation rounds. |
| `/atlassian-pm:create-story` | Story + subtasks. `--no-subtasks` for story only (add subtasks later). `--thorough` for full workflow. |
| `/atlassian-pm:analyze-story` | Explore codebase → create subtasks + Implementation Hints. `--skip-explore` when paths known. `--thorough` for ITERATE. |
| `/atlassian-pm:create-task` | Create standalone task: tech-debt, bug, chore, spike. Vibe default: auto-detect type. |
| `/atlassian-pm:bug-triage` | Bug intake → P1/P2/P3 severity → dedup → assign. `--no-assign` to skip assignment gate. |
| `/atlassian-pm:search-issues` | Dedup check before creating |
| `/atlassian-pm:spec-to-stories` | Convert Confluence spec page → batch User Stories |
| **Scrumban Flow** | |
| `/atlassian-pm:flow-check` | Board health snapshot + replenishment trigger |
| `/atlassian-pm:start-ticket` | Read AC + transition to In Progress (WIP gate enforced) |
| `/atlassian-pm:ship-to-qa` | Post PR + preview URLs → transition to Ready for QA |
| `/atlassian-pm:close-sprint` | Triage incomplete → move → Confluence review |
| `/atlassian-pm:standup-report` | Daily standup digest per assignee |
| `/atlassian-pm:plan-sprint` | Capacity-based sprint allocation _(release forecasting)_ |
| `/atlassian-pm:reschedule-sprint` | Bulk-shift issue dates across a sprint |
| `/atlassian-pm:map-dependencies` | Critical path + swim lane dependency analysis |
| **Quality & Updates** | |
| `/atlassian-pm:verify-issue` | ADF format + INVEST criteria check (A1-A6) |
| `/atlassian-pm:sync-artifacts` | Bidirectional sync: Story ↔ Sub-tasks ↔ Confluence |
| `/atlassian-pm:update-story` | Edit Story — ACs, scope, description |
| `/atlassian-pm:update-epic` | Edit Epic — scope, RICE, metrics |
| `/atlassian-pm:update-task` | Edit Task — format, details |
| `/atlassian-pm:update-subtask` | Edit Sub-task — format, content |
| `/atlassian-pm:assign-issue` | Assign issue (bypasses MCP silent failure) |
| **QA** | |
| `/atlassian-pm:create-testplan` | Test Plan + QA subtasks from Story ACs |
| `/atlassian-pm:execute-testplan` | Run test cases via Playwright → create bug tickets |
| **Confluence** | |
| `/atlassian-pm:create-doc` | Create page: tech-spec, adr, parent |
| `/atlassian-pm:update-doc` | Update or move a Confluence page |
| `/atlassian-pm:plan-release` | Multi-sprint release plan + Confluence page + Fix Version |
| `/atlassian-pm:release-notes` | Generate Confluence release notes from Fix Version |
| **Utilities** | |
| `/atlassian-pm:scan-tech-debt` | Aggregate tech-debt → Effort×Impact matrix on Confluence |
| `/atlassian-pm:activity-report` | Work activity report from session history |
| `/atlassian-pm:atlassian-scripts` | Python scripts for complex Jira/Confluence ops |

---

## Common Workflows

### Workflow A: Vibe coding (fastest path)

Type directly in Claude Code — no slash command needed:

```text
vibe plan "coupon redemption at checkout for logged-in users"

สร้าง feature ระบบ push notification บนมือถือ

แตก feature video upload พร้อม progress bar ออกเป็น tasks ให้หน่อยครับ
```

Or use the fast-path command:

```text
/vibe-full "coupon redemption at checkout"
```

**Output:** Epic + 3-5 stories + subtasks with Implementation Hints (entry point, pattern, test command). Team member runs: `implement {{PROJECT_KEY}}-123`

### Workflow B: Analyze existing story → subtasks

Type directly:

```text
วิเคราะห์ Story {{PROJECT_KEY}}-123 จากนั้นสร้าง subtasks สำหรับทีม Engineer

analyze story {{PROJECT_KEY}}-456 and create implementation subtasks with hints

ช่วย break down {{PROJECT_KEY}}-789 ออกเป็น subtasks พร้อม implementation hints
```

Or use the slash command:

```text
/atlassian-pm:analyze-story {{PROJECT_KEY}}-XXX
```

### Workflow C: New feature from scratch

```
1. /atlassian-pm:create-epic     → Epic + Confluence epic page
2. /atlassian-pm:create-story    → User Stories with subtasks under the epic
```

Or use the fast-path: `/epic-full`

### Workflow D: Bug report

Type directly:

```text
bug: ผู้ใช้ checkout ไม่ได้เมื่อ coupon code มีตัวอักษรพิเศษ

video player crash เมื่อ seek ไปที่ timestamp ที่ยังไม่ได้ buffer — P2

bug report: API returns 500 when user has more than 50 items in cart
```

Or use the fast-path: `/bug-full`

### Workflow E: Scrumban daily flow

```
1. /atlassian-pm:flow-check           → board health + replenish Ready queue if low
2. /atlassian-pm:start-ticket {{PROJECT_KEY}}-XXX  → read AC + move to In Progress
3. /atlassian-pm:ship-to-qa {{PROJECT_KEY}}-XXX    → post PR + preview URLs + transition to Ready for QA
```

### Workflow F: Sprint close with retrospective

```
1. /atlassian-pm:close-sprint           → triage incomplete issues
2. /atlassian-pm:retrospective-analyst  → generate retro + Confluence page
```

Or use the fast-path: `/sprint-close-full`

### Workflow G: Verify issue quality

```text
verify {{PROJECT_KEY}}-123 --with-subtasks --fix

ตรวจสอบ ticket {{PROJECT_KEY}}-456 พร้อม subtasks ทั้งหมด และ fix ที่มีปัญหา
```

Or use the slash command:

```
/atlassian-pm:verify-issue {{PROJECT_KEY}}-XXX --with-subtasks
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
| `code-explorer` | Maps codebase before creating subtasks | haiku |
| `issue-bootstrap` | Pre-fetches issue context efficiently | haiku |
| `jira-search` | Duplicate detection with confidence scoring | haiku |
| `quality-gate` | Scores ADF content before writes | sonnet |
| `pr-description-writer` | Generates PR description from branch + issue | haiku |
| `pr-review-jira-sync` | Syncs merged PR back to Jira | haiku |
| `velocity-tracker` | Tracks velocity history in config | haiku |
| `sprint-transition-agent` | Batch sprint issue moves + state transitions | haiku |
| `spec-parser-agent` | Parse Confluence spec → structured requirements | haiku |
| `adf-surgeon` | Structural ADF repair for Jira quirks | haiku |
| `estimation-calibrator` | SP calibration from historical similarity | haiku |
| `bug-evidence-writer` | ADF bug description from test failure evidence | haiku |
| `story-writer` | Writes ADF content for issues | sonnet |
| `alignment-checker` | Checks story-subtask alignment | sonnet |
| `backlog-groomer` | WSJF scoring + sprint-readiness checks | sonnet |
| `retrospective-analyst` | Sprint retro + Confluence page | sonnet |
| `sprint-planner` | Capacity + distribution analysis | sonnet |
| `risk-forecaster` | 4-dimension delivery risk scoring per sprint | sonnet |
| `team-pattern-advisor` | Multi-sprint strategic pattern analysis | sonnet |
| `test-case-runner` | Execute single Playwright test case | sonnet |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `acli not found` | `brew install acli` then re-run `/atlassian-pm:setup` |
| MCP tools not found | Restart Claude Code after running `/atlassian-pm:setup` |
| `atlassian-cache: Failed to connect` | Run `/atlassian-pm:setup` to install the venv. After any plugin update, re-run setup to rebuild it. |
| QG keeps failing | Run `/atlassian-pm:verify-issue KEY --fix` |
| Stale issue data | Cache auto-invalidates after writes; force with `cache_invalidate(key)` |
| Subtask has wrong parent | Enforced by HR5: MCP create → verify parent → acli edit |
| Sprint ID mismatch | Never hardcode sprint IDs; always resolved via `jira_get_sprints_from_board()` |
| Reinstalled plugin, venv missing | Run `/atlassian-pm:setup` — detects missing venv, re-runs `uv sync` automatically |

Full troubleshooting reference: `references/troubleshooting.md`

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

Full rule definitions: `references/hr-rules.md`
