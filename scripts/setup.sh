#!/bin/bash
# Setup jira-generator: skills, CLI tools, and global Claude config
# Safe to run multiple times (idempotent)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== jira-generator setup ==="
echo "Project: $PROJECT_DIR"
echo ""

# --- 0. Check project config ---
CONFIG_FILE="$PROJECT_DIR/.claude/project-config.json"
CONFIG_TEMPLATE="$PROJECT_DIR/.claude/project-config.json.template"

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

# --- 1. Install sync-skills CLI ---
echo "[1/4] Installing sync-skills CLI..."
mkdir -p "$HOME/.local/bin"

SYNC_SRC="$SCRIPT_DIR/sync-skills"
SYNC_DST="$HOME/.local/bin/sync-skills"

if [ -L "$SYNC_DST" ]; then
  existing=$(readlink "$SYNC_DST")
  if [ "$existing" = "$SYNC_SRC" ]; then
    echo "  already installed"
  else
    rm "$SYNC_DST"
    ln -s "$SYNC_SRC" "$SYNC_DST"
    echo "  updated (was: $existing)"
  fi
elif [ -f "$SYNC_DST" ]; then
  rm "$SYNC_DST"
  ln -s "$SYNC_SRC" "$SYNC_DST"
  echo "  replaced file with symlink"
else
  ln -s "$SYNC_SRC" "$SYNC_DST"
  echo "  installed"
fi

# --- 2. Sync skills to ~/.claude/skills/ ---
echo ""
echo "[2/4] Syncing skills to ~/.claude/skills/..."
"$SYNC_SRC"

# --- 3. Add Atlassian config to ~/.claude/CLAUDE.md ---
echo ""
echo "[3/4] Configuring ~/.claude/CLAUDE.md..."
mkdir -p "$HOME/.claude"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

if [ -f "$CLAUDE_MD" ] && grep -q "Atlassian Settings" "$CLAUDE_MD"; then
  echo "  Atlassian settings already present"
else
  # Append config block (update values from .claude/project-config.json)
  cat >> "$CLAUDE_MD" << 'ATLASSIAN_CONFIG'

## Atlassian Settings

> **Full config:** `jira-generator/.claude/project-config.json` — team, services, environments, custom fields

| Setting | Value |
| --- | --- |
| Jira | `your-site.atlassian.net` / Project: `BEP` |
| Date Fields | `{{START_DATE_FIELD}}` (Start), `{{SPRINT_FIELD}}` (Sprint) |

**Dynamic lookup:** Board → `jira_get_agile_boards(project_key="{{PROJECT_KEY}}")` · Sprint → `jira_get_sprints_from_board(board_id, state="future")`

**Assign:** `acli jira workitem assign -k "KEY" -a "email" -y` (MCP assignee broken)

## Development Workflow

### When referencing Jira issues ({{PROJECT_KEY}}-XXX)

**Before implement:**
1. Read issue via MCP `jira_get_issue` — understand AC, scope, technical notes
2. Read sub-tasks for implementation details

**After implement:**
1. Add Jira comment via MCP `jira_add_comment`:
   - What was implemented/changed
   - Files modified
   - Deviations from AC (if any)

### Daily Ops Tool Selection

| Operation | Tool |
| --- | --- |
| Read issue | MCP `jira_get_issue` |
| Search issues | MCP `jira_search` |
| Add comment | MCP `jira_add_comment` |
| Update issue fields | MCP `jira_update_issue` |
| Read Confluence | MCP `confluence_get_page` |
| Update Confluence | MCP `confluence_update_page` |
| Complex formatting | `/atlassian-scripts` |
| Create/manage issues | Skill commands (`/create-story`, `/verify-issue`, etc.) |
ATLASSIAN_CONFIG
  echo "  added Atlassian settings and workflow"
fi

# --- 4. Configure git smudge/clean filter ---
echo ""
echo "[4/4] Configuring git filters..."
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
