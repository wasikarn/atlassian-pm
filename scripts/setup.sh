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

# --- 1. Configure git smudge/clean filter ---
echo ""
echo "[1/1] Configuring git filters..."
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
