#!/bin/bash
# Setup atlassian-pm: skills, CLI tools, and global Claude config
# Safe to run multiple times (idempotent)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== atlassian-pm setup ==="
echo "Project: $PROJECT_DIR"
echo ""

# --- deps. Check + install dependencies (idempotent) ---
echo "[deps] Checking dependencies..."

check_dep() { command -v "$1" &>/dev/null; }

if ! check_dep acli; then
  echo "  Installing acli via Homebrew..."
  brew tap atlassian/homebrew-acli
  brew install acli
fi

if ! check_dep uv; then
  echo "  Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if [ -d "$PROJECT_DIR/mcp-servers/atlassian-cache" ]; then
  echo "  Installing atlassian-cache venv..."
  UV_BIN="${HOME}/.local/bin/uv"
  command -v uv &>/dev/null && UV_BIN="uv"
  # Fallback: derive data dir using Claude Code naming convention "{plugin}-{marketplace}"
  if [ -z "$CLAUDE_PLUGIN_DATA" ]; then
    CLAUDE_PLUGIN_DATA="$HOME/.claude/plugins/data/atlassian-pm-atlassian-pm"
  fi
  mkdir -p "$CLAUDE_PLUGIN_DATA"
  UV_PROJECT_ENVIRONMENT="$CLAUDE_PLUGIN_DATA/venv" "$UV_BIN" sync --project "$PROJECT_DIR/mcp-servers/atlassian-cache" --quiet
  cp "$PROJECT_DIR/mcp-servers/atlassian-cache/pyproject.toml" "$CLAUDE_PLUGIN_DATA/pyproject.toml" 2>/dev/null || true

  # Verify MCP server dependencies are actually importable
  VENV_PYTHON="$CLAUDE_PLUGIN_DATA/venv/bin/python"
  if [ ! -f "$VENV_PYTHON" ]; then
    echo "  WARNING: venv not found at $CLAUDE_PLUGIN_DATA/venv — uv sync may have failed"
  else
    echo "  Verifying atlassian-cache dependencies..."
    MISSING=$("$VENV_PYTHON" - << 'PYCHECK' 2>&1
import sys
failed = []
for pkg, import_name in [("mcp", "mcp"), ("sqlite-vec", "sqlite_vec"), ("sentence-transformers", "sentence_transformers")]:
    try:
        __import__(import_name)
    except ImportError:
        failed.append(pkg)
if failed:
    print("MISSING: " + ", ".join(failed))
    sys.exit(1)
PYCHECK
)
    if [ $? -eq 0 ]; then
      echo "  [OK] mcp, sqlite-vec, sentence-transformers"
    else
      echo "  [FAIL] $MISSING"
      echo "  Try: UV_PROJECT_ENVIRONMENT=\"$CLAUDE_PLUGIN_DATA/venv\" uv sync --project mcp-servers/atlassian-cache"
    fi
  fi

  # --- Register atlassian-cache in ~/.claude.json (user-scoped) ---
  # Plugin .mcp.json is intentionally empty to avoid duplicate registration.
  # Claude Code loads .mcp.json from BOTH marketplace and cache dirs; if both
  # had the server, it triggers "skipped — same command/URL" on every startup.
  # User-scoped registration in ~/.claude.json avoids this entirely.
  echo "  Registering atlassian-cache MCP server in ~/.claude.json..."

  _ATLASPM_MARKETPLACE="$HOME/.claude/plugins/marketplaces/atlassian-pm"
  export _ATLASPM_MARKETPLACE _CLAUDE_PLUGIN_DATA="$CLAUDE_PLUGIN_DATA"

  python3 - << 'PYEOF'
import json, os, sys

claude_json = os.path.expanduser("~/.claude.json")
marketplace_dir = os.environ["_ATLASPM_MARKETPLACE"]
data_dir = os.environ["_CLAUDE_PLUGIN_DATA"]

desired = {
    "command": "uv",
    "args": [
        "run", "--project", "mcp-servers/atlassian-cache",
        "mcp-servers/atlassian-cache/server.py"
    ],
    "cwd": marketplace_dir,
    "env": {
        "PYTHONPATH": marketplace_dir + "/scripts",
        "UV_PROJECT_ENVIRONMENT": data_dir + "/venv",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    }
}

config = {}
if os.path.exists(claude_json):
    with open(claude_json) as f:
        config = json.load(f)

existing = config.get("mcpServers", {}).get("atlassian-cache")
if existing == desired:
    print("  [OK] atlassian-cache already registered in ~/.claude.json")
    sys.exit(0)

config.setdefault("mcpServers", {})["atlassian-cache"] = desired
with open(claude_json, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
print("  [OK] atlassian-cache registered in ~/.claude.json")
PYEOF

  # Clear plugin .mcp.json files so the user-scoped entry above is the only source.
  # Prevents "skipped — same command/URL" duplicate warning on every startup.
  _EMPTY='{"mcpServers": {}}'
  printf '%s\n' "$_EMPTY" > "$HOME/.claude/plugins/marketplaces/atlassian-pm/.mcp.json" 2>/dev/null || true
  python3 -c "
import glob, os
for f in glob.glob(os.path.expanduser('~/.claude/plugins/cache/atlassian-pm/atlassian-pm/*/.mcp.json')):
    open(f, 'w').write('{\"mcpServers\": {}}\n')
" 2>/dev/null || true
fi

echo ""

# --- migrate. Remove legacy cache (pre-CLAUDE_PLUGIN_DATA) ---
LEGACY_CACHE="$HOME/.cache/jira-generator"
if [ -d "$LEGACY_CACHE" ]; then
  echo "[migrate] Removing legacy cache at $LEGACY_CACHE ..."
  trash "$LEGACY_CACHE"
  echo "  Done. DB now stored in CLAUDE_PLUGIN_DATA (plugin data dir)."
  echo ""
fi

# --- 0. Check project config ---
CONFIG_FILE="$PROJECT_DIR/.claude/project-config.json"
# Prefer config/ template (more complete), fall back to .claude/ template
if [ -f "$PROJECT_DIR/config/project-config.json.template" ]; then
  CONFIG_TEMPLATE="$PROJECT_DIR/config/project-config.json.template"
else
  CONFIG_TEMPLATE="$PROJECT_DIR/.claude/project-config.json.template"
fi
TEAM_DETAIL_FILE="$PROJECT_DIR/.claude/project-config-team-detail.json"
TEAM_DETAIL_TEMPLATE="$PROJECT_DIR/.claude/project-config-team-detail.json.template"

_config_has_placeholder() { grep -qE "acme-corp\.atlassian\.net|YOUR-INSTANCE|YOUR_PROJECT_KEY" "$1" 2>/dev/null; }

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

if [ ! -f "$TEAM_DETAIL_FILE" ]; then
  if [ -f "$TEAM_DETAIL_TEMPLATE" ]; then
    cp "$TEAM_DETAIL_TEMPLATE" "$TEAM_DETAIL_FILE"
    echo "Created .claude/project-config-team-detail.json from template"
    echo "  → Edit with your team git evidence and velocity history"
    echo ""
  fi
fi

# --- 1. Add Atlassian config to ~/.claude/CLAUDE.md ---
echo ""
echo "[1/2] Configuring ~/.claude/CLAUDE.md..."
mkdir -p "$HOME/.claude"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

# Read real values from project-config.json (skip if still placeholder)
JIRA_SITE=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('jira',{}).get('site','your-site.atlassian.net'))" 2>/dev/null || echo "your-site.atlassian.net")
PROJECT_KEY=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('jira',{}).get('project_key','YOUR_KEY'))" 2>/dev/null || echo "YOUR_KEY")

if _config_has_placeholder "$CONFIG_FILE" 2>/dev/null; then
  echo "  config has placeholder values — CLAUDE.md update skipped (run /atlassian-pm:setup to configure)"
elif [ -f "$CLAUDE_MD" ] && grep -q "Atlassian Settings" "$CLAUDE_MD"; then
  echo "  Atlassian settings already present"
else
  cat >> "$CLAUDE_MD" << ATLASSIAN_CONFIG

## Atlassian Settings

> **Full config:** \`atlassian-pm/.claude/project-config.json\` — team, services, environments, custom fields

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
if ! git -C "$PROJECT_DIR" rev-parse --git-dir &>/dev/null; then
  echo "  skipped (not a git repository — plugin installed from cache)"
else
  CURRENT_SMUDGE=$(git -C "$PROJECT_DIR" config --get filter.project-config.smudge 2>/dev/null || true)
  EXPECTED_SMUDGE="python3 scripts/git_filter.py --smudge"

  if [ "$CURRENT_SMUDGE" = "$EXPECTED_SMUDGE" ]; then
    echo "  already configured"
  else
    git -C "$PROJECT_DIR" config filter.project-config.smudge "python3 scripts/git_filter.py --smudge"
    git -C "$PROJECT_DIR" config filter.project-config.clean "python3 scripts/git_filter.py --clean"
    echo "  configured (auto placeholder conversion)"
  fi
fi

# --- Backup config to ~/.config/atlassian/ ---
if [ -f "$CONFIG_FILE" ] && ! _config_has_placeholder "$CONFIG_FILE"; then
  mkdir -p "$HOME/.config/atlassian"
  cp "$CONFIG_FILE" "$HOME/.config/atlassian/project-config.json"
  echo ""
  echo "[backup] project-config.json → ~/.config/atlassian/project-config.json"
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
