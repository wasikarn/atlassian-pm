#!/bin/bash
# Setup jira-generator: skills, CLI tools, and global Claude config
# Safe to run multiple times (idempotent)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== jira-generator setup ==="
echo "Project: $PROJECT_DIR"
echo ""

# --- deps. Check + install dependencies (idempotent) ---
echo "[deps] Checking dependencies..."

check_dep() { command -v "$1" &>/dev/null; }

if ! check_dep acli; then
  echo "  Installing acli via Homebrew..."
  brew install atlassian-cli
fi

if ! check_dep uv; then
  echo "  Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if [ -d "$PROJECT_DIR/mcp-servers/jira-cache-server" ]; then
  echo "  Installing jira-cache-server venv..."
  UV_BIN="${HOME}/.local/bin/uv"
  command -v uv &>/dev/null && UV_BIN="uv"
  "$UV_BIN" sync --project "$PROJECT_DIR/mcp-servers/jira-cache-server" --extra embeddings --quiet
fi

echo ""

# --- 0. Check project config ---
CONFIG_FILE="$PROJECT_DIR/.claude/project-config.json"
CONFIG_TEMPLATE="$PROJECT_DIR/config/project-config.json.template"

if [ ! -f "$CONFIG_FILE" ]; then
  if [ -f "$CONFIG_TEMPLATE" ]; then
    cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
    echo "Created .claude/project-config.json from template"
    echo "  → Edit with your real values: team, Jira site, domains, service paths"
    echo ""
  else
    echo "WARNING: No project-config.json or template found"
  fi
fi

# --- 1. Add Atlassian config to ~/.claude/CLAUDE.md ---
echo ""
echo "[1/2] Configuring ~/.claude/CLAUDE.md..."
mkdir -p "$HOME/.claude"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

# Read real values from project-config.json
JIRA_SITE=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('jira',{}).get('site','your-site.atlassian.net'))" 2>/dev/null || echo "your-site.atlassian.net")
PROJECT_KEY=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('jira',{}).get('project_key','YOUR_KEY'))" 2>/dev/null || echo "YOUR_KEY")

if [ -f "$CLAUDE_MD" ] && grep -q "Atlassian Settings" "$CLAUDE_MD"; then
  echo "  Atlassian settings already present"
else
  cat >> "$CLAUDE_MD" << ATLASSIAN_CONFIG

## Atlassian Settings

> **Full config:** \`jira-generator/.claude/project-config.json\` — team, services, environments, custom fields

| Setting | Value |
| --- | --- |
| Jira | \`${JIRA_SITE}\` / Project: \`${PROJECT_KEY}\` |
| Date Fields | \`{{START_DATE_FIELD}}\` (Start), \`{{SPRINT_FIELD}}\` (Sprint) |

**Dynamic lookup:** Board → \`jira_get_agile_boards(project_key="${PROJECT_KEY}")\` · Sprint → \`jira_get_sprints_from_board(board_id, state="future")\`

**Assign:** \`acli jira workitem assign -k "KEY" -a "email" -y\` (MCP assignee broken)

## Development Workflow

### When referencing Jira issues (${PROJECT_KEY}-XXX)

**Before implement:**
1. Read issue via MCP \`jira_get_issue\` — understand AC, scope, technical notes
2. Read sub-tasks for implementation details

**After implement:**
1. Add Jira comment via MCP \`jira_add_comment\`:
   - What was implemented/changed
   - Files modified
   - Deviations from AC (if any)

### Daily Ops Tool Selection

| Operation | Tool |
| --- | --- |
| Read issue | MCP \`jira_get_issue\` |
| Search issues | MCP \`jira_search\` |
| Add comment | MCP \`jira_add_comment\` |
| Update issue fields | MCP \`jira_update_issue\` |
| Read Confluence | MCP \`confluence_get_page\` |
| Update Confluence | MCP \`confluence_update_page\` |
| Complex formatting | \`/atlassian-scripts\` |
| Create/manage issues | Skill commands (\`/story-full\`, \`/verify-issue\`, etc.) |
ATLASSIAN_CONFIG
  echo "  added Atlassian settings (site: ${JIRA_SITE}, project: ${PROJECT_KEY})"
fi

# --- 2. Configure git smudge/clean filter ---
echo ""
echo "[2/2] Configuring git filters..."
CURRENT_SMUDGE=$(cd "$PROJECT_DIR" && git config --get filter.project-config.smudge 2>/dev/null || true)
EXPECTED_SMUDGE="python3 scripts/git_filter.py --smudge"

if [ "$CURRENT_SMUDGE" = "$EXPECTED_SMUDGE" ]; then
  echo "  already configured"
else
  cd "$PROJECT_DIR"
  git config filter.project-config.smudge "python3 scripts/git_filter.py --smudge"
  git config filter.project-config.clean "python3 scripts/git_filter.py --clean"
  echo "  configured (auto placeholder conversion)"
fi

# --- Check PATH ---
echo ""
if echo "$PATH" | tr ':' '\n' | grep -q "$HOME/.local/bin"; then
  echo "=== Setup complete ==="
else
  echo "=== Setup complete ==="
  echo ""
  echo "WARNING: ~/.local/bin is not in PATH. Add to your shell profile:"
  echo '  export PATH="$HOME/.local/bin:$PATH"'
fi
