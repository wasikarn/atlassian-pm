# atlassian-pm (jira-generator)

Agile Documentation System for **{{COMPANY}} Platform** — Create Epics, User Stories, Sub-tasks, and plan Sprints via Claude Code plugin (`atlassian-pm`).

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
cp config/project-config.json.template .claude/project-config.json
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

### 4. Load Plugin (Development Mode)

```bash
# Load plugin for this session
claude --plugin-dir /path/to/jira-generator

# Or add to your Claude Code config for permanent use:
# ~/.claude/settings.json → "pluginDirs": ["/path/to/jira-generator"]
```

Skills are available as `/atlassian-pm:<name>` (e.g. `/atlassian-pm:story-full`).

### 5. Setup Jira Cache Server (Optional)

Local SQLite cache for Jira data — reduces token consumption by 80-90% for repeated queries.

```bash
# Create venv in cache directory
python3 -m venv ~/.cache/jira-generator/jira-cache-server/.venv
source ~/.cache/jira-generator/jira-cache-server/.venv/bin/activate
pip install -r mcp-servers/jira-cache-server/requirements.txt
```

The `.mcp.json` at plugin root auto-registers `jira-cache-server` when loaded via `--plugin-dir`.

### Verify Setup

```bash
# Validate plugin structure
claude plugin validate .

# Check acli
acli jira project list --server https://your-site.atlassian.net

# In Claude Code: /atlassian-pm:search-issues → should list issues
```

---

## Commands

Load the plugin (`claude --plugin-dir .`) then type `/atlassian-pm:<command>`.

### Jira — Issue Creation

| Command | Description |
| ------- | ----------- |
| `/atlassian-pm:story-full` | Create Story + Sub-tasks in one go (preferred) |
| `/atlassian-pm:create-epic` | Create Epic + Confluence Epic Doc with RICE scoring |
| `/atlassian-pm:create-task` | Create Task: `tech-debt`, `bug`, `chore`, or `spike` |
| `/atlassian-pm:analyze-story ABC-XXX` | Read Story → explore codebase → create Sub-tasks |
| `/atlassian-pm:create-testplan ABC-XXX` | Create Test Plan + [QA] Sub-tasks from Story |

### Jira — Issue Updates

| Command | Description |
| ------- | ----------- |
| `/atlassian-pm:update-story ABC-XXX` | Edit Story — add/edit ACs, scope |
| `/atlassian-pm:update-epic ABC-XXX` | Edit Epic — adjust scope, RICE, metrics |
| `/atlassian-pm:update-task ABC-XXX` | Edit Task — migrate format, add details |
| `/atlassian-pm:update-subtask ABC-XXX` | Edit Sub-task — format, content |
| `/atlassian-pm:sync-alignment ABC-XXX` | Sync Story + Sub-tasks bidirectional (+ Confluence if exists) |

### Jira — Sync & Quality

| Command | Description |
| ------- | ----------- |
| `/atlassian-pm:verify-issue ABC-XXX` | Check ADF format, INVEST criteria, language |
| `/atlassian-pm:search-issues` | Search before creating (prevent duplicates) |

`/atlassian-pm:verify-issue` flags: `--with-subtasks` (batch check), `--fix` (auto-fix), `--dry-run` (report only)

### Jira — Planning & Analysis

| Command | Description |
| ------- | ----------- |
| `/atlassian-pm:plan-sprint` | Sprint planning: carry-over + capacity + assign |
| `/atlassian-pm:dependency-chain` | Dependency graph, critical path, swim lanes |
| `/atlassian-pm:activity-report` | Generate work activity report from claude-mem |

`/atlassian-pm:plan-sprint` options: `--sprint 123` (target sprint), `--carry-over-only` (analysis only)

### Confluence — Documentation

| Command | Description |
| ------- | ----------- |
| `/atlassian-pm:create-doc` | Create Confluence page: `tech-spec`, `adr`, `parent` |
| `/atlassian-pm:update-doc` | Update or move a Confluence page |
| `/optimize-context` | Audit + compress CLAUDE.md passive context |

---

## Usage Examples

### Create a Full Feature (End-to-End)

```text
/atlassian-pm:search-issues        → Check no duplicates exist
/atlassian-pm:create-epic          → Create Epic + Confluence doc
/atlassian-pm:story-full           → Create Story + Sub-tasks in one go
/atlassian-pm:create-testplan      → Create [QA] Sub-tasks (optional)
/atlassian-pm:verify-issue ABC-XXX → Verify quality
```

**Example:** `/atlassian-pm:story-full` → "Build a coupon system for admin" → Claude generates Story + Sub-tasks `[BE]`, `[FE-Admin]`

### Plan a Sprint

```text
/atlassian-pm:plan-sprint   → 8 phases: Discovery → Capacity → Carry-over →
                              Prioritize → Distribute → Risk → Review → Execute
```

### Update + Cascade Changes

```text
/atlassian-pm:update-story ABC-XXX     → Edit Story only
/atlassian-pm:sync-alignment ABC-XXX   → + cascade to Sub-tasks + sync Confluence docs
```

---

## Project Structure

```text
.claude-plugin/plugin.json          <- Plugin manifest (name: atlassian-pm)
.mcp.json                           <- MCP server config (jira-cache-server)

skills/                             <- Skill definitions (1 dir = 1 slash command)
├── create-{epic,task,doc,testplan}/
├── update-{epic,story,task,subtask,doc}/
├── analyze-story/
├── story-full/                     <- Composite: PO + TA in one workflow
├── sync-alignment/                 <- Bidirectional sync (Jira + Confluence)
├── plan-sprint/                    <- Sprint planning: carry-over + capacity + assign
├── dependency-chain/               <- Critical path + swim lane analysis
├── search-issues/, verify-issue/, activity-report/, assign/
├── atlassian-scripts/              <- Python REST API scripts (non-user-invocable)
│   ├── lib/                        <- auth, jira_api, converters, exceptions
│   └── scripts/                    <- 16 utility scripts
└── shared-references/              <- Reusable docs loaded by skills (23 files)
    ├── templates.md                <- All ADF templates (Epic, Story, Sub-task, Task)
    ├── tools.md, writing-style.md, verification-checklist.md
    ├── troubleshooting.md, hr-rules.md
    └── ...

agents/                             <- 8 subagent definitions
├── code-explorer.md (haiku)        <- Codebase exploration
├── issue-reader.md (haiku)         <- Fast Jira issue fetch
├── jira-search.md (haiku)          <- JQL search + dedup
├── issue-bootstrap.md (haiku)      <- Pre-gather full issue context
├── quality-gate.md (haiku)         <- ADF quality scoring
├── story-writer.md (sonnet)        <- ADF JSON generation
├── alignment-checker.md (sonnet)   <- Epic→Story→Subtask alignment
└── sprint-planner.md (opus)        <- Sprint planning

hooks/                              <- 39 Python hook scripts
├── hooks.json                      <- Plugin hook manifest (${CLAUDE_PLUGIN_ROOT})
├── hooks_lib.py, hooks_state.py    <- Shared libraries
└── pre_hr*.py, post_hr*.py, ...    <- HR enforcement hooks

mcp-servers/jira-cache-server/      <- MCP server: local Jira cache (SQLite+FTS5)
├── server.py                       <- MCP entry point + 10 tool handlers
└── jira_cache/                     <- cache.py + embeddings.py

scripts/
├── setup.sh, git_filter.py         <- Setup + git smudge/clean filter
├── sprint/                         <- Sprint batch utilities (5 scripts)
└── confluence/                     <- Confluence page scripts

config/project-config.json.template <- Template for instance-specific config
tasks/                              <- Generated ADF JSON outputs (gitignored)
CLAUDE.md                           <- Agent instructions (passive context)
```

> **Note:** jira-cache-server venv stored at `~/.cache/jira-generator/jira-cache-server/.venv/` (~643MB ML deps, outside project tree).

## Configuration System

All project-specific values (Jira site, team, services, domains) live in `.claude/project-config.json` — the **single source of truth**. The repo tracks only the `.template` version with safe placeholder values; real config is gitignored.

### How It Works

```text
Git repo (committed):  ABC-XXX    ← always placeholders
                          │
                    [smudge filter]            ← on checkout/pull
                          ↓
Working tree:          ABC-XXX                ← real values (local dev)
                          │
                    [clean filter]             ← on add/commit
                          ↓
Git staging:           ABC-XXX    ← always placeholders
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
cp config/project-config.json.template .claude/project-config.json

# 2. Edit with your values: team, Jira site, domains, service paths
vi .claude/project-config.json

# 3. Run setup (configures git filters)
./scripts/setup.sh
```

> **Manual override:** `python scripts/configure_project.py --apply` / `--revert --apply` for debugging or bulk conversion without git filters.

## Tips

- **Always search first:** `/atlassian-pm:search-issues` before creating to prevent duplicates
- **Always verify after:** `/atlassian-pm:verify-issue ABC-XXX` after creating/updating
- **Language:** Thai + English transliteration for technical terms (endpoint, API, component)
- **Format:** Jira descriptions use ADF format — Claude handles this via `acli --from-json`
- **Codebase first:** `/atlassian-pm:analyze-story` always explores codebase before creating Sub-tasks
- **Cache server:** Use `cache_sprint_issues` before sprint planning for 80%+ token savings
- **Hot-reload:** After editing skill/agent files, use `/reload-plugins` in Claude Code
