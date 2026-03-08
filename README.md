# Jira Generator

Agile Documentation System for **{{COMPANY}} Platform** — Create Epics, User Stories, Sub-tasks, and plan Sprints via Claude Code skills.

## Architecture

```text
Claude Code ──skills──> acli (ADF JSON) ──> Jira Cloud
    │                                         ↑
    ├──MCP──> mcp-atlassian ─────────────────┘
    │                                   ↑
    ├──MCP──> jira-cache-server ───SQLite+FTS5 (local cache)
    │                              └─> Jira REST API v3
    ├──MCP──> Confluence, Figma, GitHub
    │
    └──Python──> atlassian-scripts/lib/ (REST API)
```

**Key design decisions:**

- **Descriptions** always via `acli --from-json` (ADF format) — MCP produces ugly output
- **Fields** (assignee, sprint, labels) via MCP `jira_update_issue`
- **Sub-tasks** use two-step: MCP create (with parent) → acli edit (description)
- **Heavy ML deps** (PyTorch, sentence-transformers) isolated in venv outside project tree

## Prerequisites

| Tool | Purpose | Install |
| ---- | ------- | ------- |
| [Claude Code](https://claude.com/claude-code) | AI agent runtime | `npm i -g @anthropic-ai/claude-code` or VSCode extension |
| [acli](https://bobswift.atlassian.net/wiki/spaces/ACLI/overview) | Jira ADF descriptions | `brew install atlassian-cli` |
| [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) | Jira/Confluence MCP | `uvx mcp-atlassian` (auto-installed) |
| Python 3.x | REST API scripts | Pre-installed on macOS |

## Setup

### 0. Create Project Config (First Time Only)

```bash
cp .claude/project-config.json.template .claude/project-config.json
# Edit with your real values: team, Jira site, domains, service paths
```

### 1. Configure acli

```bash
acli jira login --server https://your-site.atlassian.net --user <email> --token <api-token>
```

### 2. Configure MCP Servers

Add to Claude Code settings (`~/.claude/settings.json` or VSCode settings):

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://your-site.atlassian.net",
        "JIRA_USERNAME": "<email>",
        "JIRA_API_TOKEN": "<api-token>",
        "CONFLUENCE_URL": "https://your-site.atlassian.net/wiki",
        "CONFLUENCE_USERNAME": "<email>",
        "CONFLUENCE_API_TOKEN": "<api-token>"
      }
    }
  }
}
```

### 3. Configure Atlassian Credentials (Python scripts)

Python scripts (`atlassian-scripts/`) load credentials from `~/.config/atlassian/.env`:

```bash
mkdir -p ~/.config/atlassian
cat > ~/.config/atlassian/.env << 'EOF'
CONFLUENCE_URL=https://your-site.atlassian.net/wiki
CONFLUENCE_USERNAME=<email>
CONFLUENCE_API_TOKEN=<api-token>
JIRA_URL=https://your-site.atlassian.net
JIRA_USERNAME=<email>
JIRA_API_TOKEN=<api-token>
EOF
```

### 4. Run Setup Script

```bash
git clone <repo-url> jira-generator
cd jira-generator

# Idempotent — safe to run multiple times
./scripts/setup.sh
```

This will:

1. Install `sync-skills` CLI to `~/.local/bin/`
2. Sync skills → `~/.claude/skills/` and agents → `~/.claude/agents/` (via symlinks)
3. Add Atlassian config to `~/.claude/CLAUDE.md`

> If `~/.local/bin` is not in your PATH: `export PATH="$HOME/.local/bin:$PATH"`

### 5. Setup Jira Cache Server (Optional)

Local SQLite cache for Jira data — reduces token consumption by 80-90% for repeated queries.

```bash
# Create venv in cache directory (not in project tree)
python3 -m venv ~/.cache/jira-generator/jira-cache-server/.venv
source ~/.cache/jira-generator/jira-cache-server/.venv/bin/activate
pip install -r .claude/skills/jira-cache-server/requirements.txt
```

Then add to MCP settings:

```json
{
  "mcpServers": {
    "jira-cache-server": {
      "command": "~/.cache/jira-generator/jira-cache-server/.venv/bin/python",
      "args": [".claude/skills/jira-cache-server/server.py"]
    }
  }
}
```

### Verify Setup

```bash
# Check skills synced
ls ~/.claude/skills/ | grep -E "jira-|confluence-"

# Check acli
acli jira project list --server https://your-site.atlassian.net

# Check MCP — open Claude Code and type: "Fetch issue BEP-1"
```

### Sync Skills After Updates

```bash
sync-skills                  # sync skills + agents
sync-skills --dry-run        # preview changes without applying
sync-skills --remove         # remove all jira-generator symlinks
sync-skills --remove --dry-run  # preview remove
```

---

## Commands

Open Claude Code in this project and type `/command`.

### Jira — Issue Creation

| Command | Description |
| ------- | ----------- |
| `/jira-story-full` | Create Story + Sub-tasks in one go (PO + TA combined) |
| `/jira-create-epic` | Create Epic + Confluence Epic Doc with RICE scoring |
| `/jira-create-story` | Create User Story from requirements (5-phase PO workflow) |
| `/jira-create-task` | Create Task: `tech-debt`, `bug`, `chore`, or `spike` |
| `/jira-analyze-story {{PROJECT_KEY}}-XXX` | Read Story → explore codebase → create Sub-tasks |
| `/jira-create-testplan {{PROJECT_KEY}}-XXX` | Create Test Plan + [QA] Sub-tasks from Story |

### Jira — Issue Updates

| Command | Description |
| ------- | ----------- |
| `/jira-update-story {{PROJECT_KEY}}-XXX` | Edit Story — add/edit ACs, scope |
| `/jira-update-epic {{PROJECT_KEY}}-XXX` | Edit Epic — adjust scope, RICE, metrics |
| `/jira-update-task {{PROJECT_KEY}}-XXX` | Edit Task — migrate format, add details |
| `/jira-update-subtask {{PROJECT_KEY}}-XXX` | Edit Sub-task — format, content |
| `/jira-story-cascade {{PROJECT_KEY}}-XXX` | Update Story + cascade to all Sub-tasks |

### Jira — Sync & Quality

| Command | Description |
| ------- | ----------- |
| `/jira-sync-alignment {{PROJECT_KEY}}-XXX` | Sync all artifacts bidirectional (Jira + Confluence) |
| `/jira-verify-issue {{PROJECT_KEY}}-XXX` | Check ADF format, INVEST criteria, language |
| `/jira-search-issues` | Search before creating (prevent duplicates) |

`/jira-verify-issue` flags: `--with-subtasks` (batch check), `--fix` (auto-fix), `--dry-run` (report only)

### Jira — Planning & Analysis

| Command | Description |
| ------- | ----------- |
| `/jira-plan-sprint` | Sprint planning: carry-over + capacity + assign |
| `/jira-dependency-chain` | Dependency graph, critical path, swim lanes |
| `/jira-activity-report` | Generate work activity report from claude-mem |

`/jira-plan-sprint` options: `--sprint 123` (target sprint), `--carry-over-only` (analysis only)

### Confluence — Documentation

| Command | Description |
| ------- | ----------- |
| `/confluence-create-doc` | Create Confluence page: `tech-spec`, `adr`, `parent` |
| `/confluence-update-doc` | Update or move a Confluence page |
| `/optimize-context` | Audit + compress CLAUDE.md passive context |

---

## Usage Examples

### Create a Full Feature (End-to-End)

```text
/jira-search-issues          → Check no duplicates exist
/jira-create-epic            → Create Epic + Confluence doc
/jira-story-full             → Create Story + Sub-tasks in one go
/jira-create-testplan        → Create [QA] Sub-tasks (optional)
/jira-verify-issue {{PROJECT_KEY}}-XXX   → Verify quality
```

**Example:** `/jira-story-full` → "Build a coupon system for admin — create, edit, delete coupons" → Claude asks for details, then auto-generates Story + Sub-tasks `[BE]`, `[FE-Admin]`

### Plan a Sprint

```text
/jira-plan-sprint       → 8 phases: Discovery → Capacity → Carry-over →
                          Prioritize → Distribute → Risk → Review → Execute
```

Claude will fetch sprint data, calculate capacity, analyze carry-over, prioritize items, match to team members, check risks, present plan for approval, then execute assignments in Jira.

### Update + Cascade Changes

```text
/jira-update-story {{PROJECT_KEY}}-XXX      → Edit Story only
/jira-story-cascade {{PROJECT_KEY}}-XXX     → + cascade to Sub-tasks
/jira-sync-alignment {{PROJECT_KEY}}-XXX    → + sync Confluence docs
```

### Analyze Dependencies

```text
/jira-dependency-chain       → Build dependency graph from sprint
                               Identify critical path + parallel execution plan
                               Generate Mermaid diagrams + swim lanes per member
```

---

## Project Structure

```text
.claude/skills/                     <- Skill definitions (1 dir = 1 command)
├── create-{epic,story,task,doc,testplan}/
├── update-{epic,story,task,subtask,doc}/
├── analyze-story/
├── story-full/                     <- Composite: PO + TA in one workflow
├── story-cascade/                  <- Update + cascade to sub-tasks
├── sync-alignment/                 <- Bidirectional sync (Jira + Confluence)
├── plan-sprint/                    <- Sprint planning: carry-over + capacity + assign
├── dependency-chain/               <- Critical path + swim lane analysis
├── search-issues/
├── verify-issue/
├── optimize-context/
├── activity-report/                <- claude-mem activity report generator
├── jira-cache-server/              <- MCP server: local Jira cache (SQLite+FTS5)
│   ├── server.py                   <- MCP entry point + 8 tool handlers
│   └── jira_cache/                 <- cache.py + embeddings.py
├── atlassian-scripts/              <- Python REST API scripts
│   ├── lib/                        <- auth, jira_api, converters, exceptions
│   └── scripts/                    <- 7 utility scripts
└── shared-references/              <- Reusable docs loaded by skills (16 files)
    ├── templates.md                <- All ADF templates (Epic, Story, Sub-task, Task)
    ├── dependency-frameworks.md    <- CPM, swim lane rules, risk scoring
    ├── tools.md                    <- Tool selection guide
    ├── writing-style.md            <- Thai + transliteration rules
    ├── verification-checklist.md   <- INVEST + quality scoring
    ├── troubleshooting.md          <- MCP errors, acli, ADF, Confluence fixes
    └── ...                         <- 12 more reference docs

scripts/
├── setup.sh                        <- Setup script (idempotent)
├── git_filter.py                   <- Git smudge/clean filter (auto placeholder conversion)
├── configure_project.py            <- Manual placeholder ↔ real value converter
├── parse_mcp_output.py             <- MCP output parser
├── sync-skills                     <- Sync skills+agents to ~/.claude/ (supports --dry-run, --remove)
├── sprint/                         <- Sprint utilities
│   ├── clear_sprint_dates.py       <- Batch clear start/due dates
│   ├── sprint_set_fields.py        <- Set SP/OE from Size field
│   ├── sprint_rank_by_date.py      <- Re-rank sprint issues by date
│   ├── sprint_subtask_alignment.py <- HR8 subtask date/OE alignment
│   └── update_sprint_goals.py      <- Sprint goals updater
├── confluence/                     <- Confluence page scripts
│   ├── create_player_architecture_page.py
│   ├── test_mermaid_animation.py
│   └── test_mermaid_forge.py
└── archive/                        <- One-off scripts (kept as reference)

tasks/                              <- Generated ADF JSON outputs (gitignored)
CLAUDE.md                           <- Agent instructions (passive context)
```

> **Note:** jira-cache-server venv is stored at `~/.cache/jira-generator/jira-cache-server/.venv/` (not in project tree) to keep the repo lightweight (~643MB of ML dependencies).

## Configuration System

All project-specific values (Jira site, team, services, domains) live in `.claude/project-config.json` — the **single source of truth**. The repo tracks only the `.template` version with safe placeholder values; real config is gitignored.

### How It Works

```text
Git repo (committed):  {{PROJECT_KEY}}-XXX    ← always placeholders
                          │
                    [smudge filter]            ← on checkout/pull
                          ↓
Working tree:          {{PROJECT_KEY}}-XXX                ← real values (local dev)
                          │
                    [clean filter]             ← on add/commit
                          ↓
Git staging:           {{PROJECT_KEY}}-XXX    ← always placeholders
```

```text
.claude/project-config.json.template   ← tracked in git (safe placeholders)
.claude/project-config.json            ← gitignored (your real values)
scripts/git_filter.py                  ← git smudge/clean filter (auto conversion)
.git/hooks/pre-commit                  ← blocks commits with sensitive data
```

After `./scripts/setup.sh`, git filters handle placeholder↔value conversion **automatically**. No manual steps needed — working tree shows real values, commits contain only placeholders.

### Placeholders

| Placeholder | Example Real Value |
| ----------- | ------------------ |
| `{{PROJECT_KEY}}` | `BEP` |
| `{{JIRA_SITE}}` | `acme-corp.atlassian.net` |
| `{{CONFLUENCE_SITE}}` | `acme-corp.atlassian.net` |
| `{{SPACE_KEY}}` | `BEP` |
| `{{START_DATE_FIELD}}` | `customfield_XXXXX` (Start Date) |
| `{{SPRINT_FIELD}}` | `customfield_YYYYY` (Sprint) |
| `{{COMPANY}}` | `Acme Corp` |
| `{{COMPANY_LOWER}}` | `acme` |
| `{{SLOT_1}}` .. `{{SLOT_N}}` | Team member names (from `project-config.json` → `team.members[]`) |

### Cloning to Another Project

```bash
# 1. Copy template to create your config
cp .claude/project-config.json.template .claude/project-config.json

# 2. Edit with your values: team, Jira site, domains, service paths
vi .claude/project-config.json

# 3. Run setup (installs CLI, syncs skills, configures git filters)
./scripts/setup.sh
```

> **Manual override:** `python scripts/configure_project.py --apply` / `--revert --apply` for debugging or bulk conversion without git filters.

## Tips

- **Always search first:** `/jira-search-issues` before creating to prevent duplicates
- **Always verify after:** `/jira-verify-issue {{PROJECT_KEY}}-XXX` after creating/updating
- **Language:** Thai + English transliteration for technical terms (endpoint, API, component)
- **Format:** Jira descriptions use ADF format — Claude handles this via `acli --from-json`
- **Codebase first:** `/jira-analyze-story` always explores codebase before creating Sub-tasks
- **Sync skills:** After adding/removing skills or agents, run `sync-skills` (or `--remove` to undo)
- **Cache server:** Use `cache_sprint_issues` before sprint planning for 80%+ token savings
