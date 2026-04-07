# Phase Scripts — /atlassian-pm:setup

Bash scripts for each setup phase. Referenced from SKILL.md.

---

## Phase 1 — `--init` Detection Script

```bash
# Define YAML config file path unconditionally — used by --init and detection
YAML_CONFIG_FILE="$HOME/.atlassian-pm.yaml"

# --init: create ~/.atlassian-pm.yaml template and exit
if [[ "${SKILL_ARGS:-}" == *"--init"* ]]; then
  if [ -f "$YAML_CONFIG_FILE" ]; then
    # Mask api_token: show last 4 chars only
    EXISTING_SITE=$(YAML_PATH="$YAML_CONFIG_FILE" python3 -c "
import os, yaml, sys
try:
  c = yaml.safe_load(open(os.environ['YAML_PATH']))
  print(c.get('jira',{}).get('site','?'))
except Exception: print('?')
" 2>/dev/null || echo "?")
    EXISTING_KEY=$(YAML_PATH="$YAML_CONFIG_FILE" python3 -c "
import os, yaml, sys
try:
  c = yaml.safe_load(open(os.environ['YAML_PATH']))
  print(c.get('jira',{}).get('project_key','?'))
except Exception: print('?')
" 2>/dev/null || echo "?")
    echo "~/.atlassian-pm.yaml already exists (site: $EXISTING_SITE, key: $EXISTING_KEY)"
    # → Ask via AskUserQuestion: buttons [Yes, overwrite] [No, keep existing]
    # → If No: print "Keeping existing ~/.atlassian-pm.yaml" and exit immediately
    # → If Yes: proceed to write template (below)
  fi
  # → Write template via Write tool (see prose below)
  # → chmod 600 immediately after
  echo ""
  echo "✓  Created ~/.atlassian-pm.yaml (chmod 600)"
  echo ""
  echo "Next steps:"
  echo "  1. Edit ~/.atlassian-pm.yaml — fill in your Jira site, project key, email, and API token"
  echo "  2. Run /atlassian-pm:setup — reads the file and completes all steps automatically"
  exit 0
fi
```

---

## Phase 1 — Config Detection Script

```bash
# macOS guard
if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: atlassian-pm setup requires macOS (Homebrew dependency)"
  exit 1
fi

# Python 3.11+ required for atlassian-cache
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
  PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
  echo "ERROR: Python 3.11+ required (found: Python $PY_VER)"
  echo "       Install: brew install python@3.11 && brew link python@3.11"
  exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python $PY_VER ✓"

# Resolve PLUGIN_ROOT from Claude Code env var (set automatically for all plugin users)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:?Error: CLAUDE_PLUGIN_ROOT not set — run this skill from within Claude Code with the plugin loaded}"

SKIP_CONFIG=false
ENV_OK=false
ACLI_OK=false
MCP_OK=false
MCP_NEWLY_ADDED=false
FIGMA_OK=false
FIGMA_NEWLY_ADDED=false
JIRA_SITE=""
PROJECT_KEY=""
SPACE_KEY=""

# Auto-restore config from backup if missing (survives plugin reinstall)
CONFIG_FILE="$PLUGIN_ROOT/.claude/project-config.json"
CONFIG_BACKUP="$HOME/.config/atlassian/atlassian-pm-config.json"
_is_placeholder() { grep -qE "acme-corp\.atlassian\.net|YOUR-INSTANCE|YOUR_PROJECT_KEY" "$1" 2>/dev/null; }
if [ ! -f "$CONFIG_FILE" ] || _is_placeholder "$CONFIG_FILE"; then
  if [ -f "$CONFIG_BACKUP" ] && ! _is_placeholder "$CONFIG_BACKUP"; then
    cp "$CONFIG_BACKUP" "$CONFIG_FILE"
    echo "  → Restored project-config.json from backup ✓"
  fi
fi

# project-config: exists and non-placeholder?
if [ -f "$CONFIG_FILE" ] && ! _is_placeholder "$CONFIG_FILE"; then
  SKIP_CONFIG=true
  JIRA_SITE=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['jira']['site'])" 2>/dev/null || echo "")
  PROJECT_KEY=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['jira']['project_key'])" 2>/dev/null || echo "")
  SPACE_KEY=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['confluence']['space_key'])" 2>/dev/null || echo "$PROJECT_KEY")
fi

# .env: exists with non-empty token?
if [ -f ~/.config/atlassian/.env ] && \
   grep -Eq "^JIRA_API_TOKEN=.+" ~/.config/atlassian/.env; then
  ENV_OK=true
fi

# acli: authenticated? (prefer exit code — more version-stable than string parsing)
if acli jira auth status &>/dev/null; then
  ACLI_OK=true
fi

# mcp-atlassian: registered? (use mcp get — output format of mcp list is undocumented)
if claude mcp get mcp-atlassian &>/dev/null; then
  MCP_OK=true
fi

# figma MCP: already registered?
if claude mcp get figma &>/dev/null; then
  FIGMA_OK=true
fi

# venv: exists in data dir?
VENV_OK=false
_PLUGIN_DATA=$(ls -d "$HOME/.claude/plugins/data/atlassian-pm-"* 2>/dev/null | sort -V | tail -1)
[ -z "$_PLUGIN_DATA" ] && _PLUGIN_DATA="$HOME/.claude/plugins/data/atlassian-pm"
if [ -f "${_PLUGIN_DATA}/venv/bin/python" ]; then
  VENV_OK=true
fi

# YAML config file detection
YAML_CONFIG=false
if [ -f "$YAML_CONFIG_FILE" ]; then
  # Use venv Python if available (guarantees pyyaml); fall back to system Python
  _VENV_PY="${_PLUGIN_DATA}/venv/bin/python"
  if [ -f "$_VENV_PY" ]; then _PARSE_PY="$_VENV_PY"; else _PARSE_PY="python3"; fi
  if [ ! -f "$_VENV_PY" ] && ! python3 -c "import yaml" 2>/dev/null; then
    echo "  config file: ~/.atlassian-pm.yaml found but pyyaml unavailable — install venv first, then re-run setup"
  else
    YAML_VALID=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" - <<'PYEOF'
import yaml, os, sys
path = os.environ["YAML_PATH"]
try:
    c = yaml.safe_load(open(path))
    placeholders = {"your-company.atlassian.net", "your-token-here", "you@company.com", "PROJ"}
    vals = [
        c["jira"]["site"],
        c["jira"]["project_key"],
        c["credentials"]["email"],
        c["credentials"]["api_token"],
    ]
    if all(vals) and not any(v in placeholders for v in vals):
        print("ok")
except Exception:
    pass
PYEOF
    )
    if [ "$YAML_VALID" = "ok" ]; then
      YAML_CONFIG=true
      echo "  config file: ~/.atlassian-pm.yaml detected ✓"
    else
      echo "  config file: ~/.atlassian-pm.yaml found but has placeholder or invalid values — using interactive setup"
    fi
  fi
fi

echo "Detection complete:"
echo "  config:      $([ "$SKIP_CONFIG" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  credentials: $([ "$ENV_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  acli auth:   $([ "$ACLI_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  mcp:         $([ "$MCP_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  venv:        $([ "$VENV_OK" = "true" ] && echo "✓ found" || echo "✗ needed (will sync)")"
echo "  figma MCP:   $([ "$FIGMA_OK" = "true" ] && echo "✓ found" || echo "- not configured (optional)")"
echo "  yaml config: $([ "$YAML_CONFIG" = "true" ] && echo "✓ found (will skip interactive questions)" || echo "- not found (interactive mode)")"
```

---

## Phase 2 — Dependency Install Script

```bash
echo "Note: Phase 2 may take 1-2 minutes on first install. Safe to re-run if interrupted."
echo ""

echo "[1/3] Checking acli..."
if command -v acli &>/dev/null; then
  echo "      acli: already installed ($(acli --version 2>/dev/null | head -1 || echo 'unknown')) ✓"
else
  echo "      acli: installing via Homebrew..."
  brew tap atlassian/homebrew-acli && brew install acli || {
    echo "ERROR: acli install failed — run: brew tap atlassian/homebrew-acli && brew install acli"
    exit 1
  }
  echo "      acli: installed ✓"
fi

echo "[2/3] Checking uv..."
if command -v uv &>/dev/null; then
  echo "      uv: already installed ($(uv --version 2>/dev/null | head -1 || echo 'unknown')) ✓"
else
  echo "      uv: installing via Homebrew..."
  brew install uv || {
    echo "ERROR: uv install failed — run: brew install uv"
    exit 1
  }
  echo "      uv: installed ✓"
fi

echo "[3/3] Syncing atlassian-cache venv..."
# Resolve data dir: prefer CLAUDE_PLUGIN_DATA env, else discover atlassian-pm-* (new naming), else fallback to atlassian-pm/
if [ -z "$CLAUDE_PLUGIN_DATA" ]; then
  CLAUDE_PLUGIN_DATA=$(ls -d "$HOME/.claude/plugins/data/atlassian-pm-"* 2>/dev/null | sort -V | tail -1)
  [ -z "$CLAUDE_PLUGIN_DATA" ] && CLAUDE_PLUGIN_DATA="$HOME/.claude/plugins/data/atlassian-pm"
fi
UV_PROJECT_ENVIRONMENT="${CLAUDE_PLUGIN_DATA}/venv" \
  uv sync --project "$PLUGIN_ROOT/mcp-servers/atlassian-cache" \
  --extra embeddings --quiet \
  && echo "      venv: ready ✓" \
  || echo "      venv: sync failed (cache features degraded — core Jira ops still work)"
```

---

## Phase 3 — YAML Config Parsing Script

```bash
if [ "$YAML_CONFIG" = "true" ]; then
  _VENV_PY="${_PLUGIN_DATA}/venv/bin/python"
  if [ -f "$_VENV_PY" ]; then _PARSE_PY="$_VENV_PY"; else _PARSE_PY="python3"; fi

  JIRA_SITE=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" -c "
import yaml, os, sys
try:
    c = yaml.safe_load(open(os.environ['YAML_PATH']))
    site = c['jira']['site'].removeprefix('https://').rstrip('/')
    print(site)
except Exception:
    print('')")

  PROJECT_KEY=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" -c "
import yaml, os, sys
try:
    c = yaml.safe_load(open(os.environ['YAML_PATH']))
    print(c['jira']['project_key'].strip().upper())
except Exception:
    print('')")

  BOARD_ID=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" -c "
import yaml, os, sys
try:
    c = yaml.safe_load(open(os.environ['YAML_PATH']))
    print(int(c['jira'].get('board_id', 0)))
except Exception:
    print('')")

  SPACE_KEY=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" -c "
import yaml, os, sys
try:
    c = yaml.safe_load(open(os.environ['YAML_PATH']))
    space = c.get('confluence', {}).get('space_key') or c['jira']['project_key']
    print(space)
except Exception:
    print('')")

  echo "  Read from config file:"
  echo "    site:        $JIRA_SITE"
  echo "    project_key: $PROJECT_KEY"
  echo "    board_id:    $BOARD_ID"
  echo "    space_key:   $SPACE_KEY"
fi
```

---

## Phase 5 — Credentials from YAML Script

```bash
if [ "$YAML_CONFIG" = "true" ] && [ "$ENV_OK" = "false" ]; then
  _VENV_PY="${_PLUGIN_DATA}/venv/bin/python"
  if [ -f "$_VENV_PY" ]; then _PARSE_PY="$_VENV_PY"; else _PARSE_PY="python3"; fi

  EMAIL=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" -c "
import yaml, os, sys
try:
    c = yaml.safe_load(open(os.environ['YAML_PATH']))
    print(c.get('credentials', {}).get('email', '').strip())
except Exception:
    print('')")

  API_TOKEN=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" -c "
import yaml, os, sys
try:
    c = yaml.safe_load(open(os.environ['YAML_PATH']))
    print(c.get('credentials', {}).get('api_token', '').strip())
except Exception:
    print('')")

  # If credentials missing from file (removed after --init), fall back to interactive
  if [ -z "$EMAIL" ] || [ -z "$API_TOKEN" ]; then
    echo "  credentials: not found in config file — asking interactively"
    # → fall through to existing interactive questions
  else
    echo "  Reading credentials from config file [token: ****$(echo "$API_TOKEN" | tail -c 5)]"
    # → proceed directly to writing ~/.config/atlassian/.env (skip interactive questions)
  fi
fi
```

---

## Phase 5 — Figma Token from YAML Script

```bash
if [ "$YAML_CONFIG" = "true" ] && [ "$FIGMA_OK" = "false" ]; then
  _VENV_PY="${_PLUGIN_DATA}/venv/bin/python"
  if [ -f "$_VENV_PY" ]; then _PARSE_PY="$_VENV_PY"; else _PARSE_PY="python3"; fi

  FIGMA_TOKEN_FROM_FILE=$(YAML_PATH="$YAML_CONFIG_FILE" "$_PARSE_PY" -c "
import yaml, os
try:
    c = yaml.safe_load(open(os.environ['YAML_PATH']))
    t = c.get('figma_token') or ''
    # Skip if placeholder
    if t.strip() in ('', 'figd_...'):
        print('')
    else:
        print(t.strip())
except Exception:
    print('')
" 2>/dev/null || echo "")

  if [ -n "$FIGMA_TOKEN_FROM_FILE" ]; then
    echo "  figma MCP: token found in config file — configuring..."
    FIGMA_TOKEN="$FIGMA_TOKEN_FROM_FILE"
    # → Skip the "Would you like to configure Figma MCP?" prompt
    # → Use FIGMA_TOKEN variable in the existing write + register steps below
  fi
fi
```

---

## Phase 6 — Finalize Script

```bash
cd "$PLUGIN_ROOT" && ./scripts/setup.sh
```

---

## Phase 6 — Health Check Script

```bash
echo ""
echo "--- Validation ---"

acli jira auth status &>/dev/null \
  && echo "  ✓  acli: authenticated" \
  || echo "  ✗  acli: auth failed — run: /atlassian-pm:setup"

claude mcp get mcp-atlassian &>/dev/null \
  && echo "  ✓  mcp-atlassian: configured" \
  || echo "  ✗  mcp-atlassian: not found — run: /atlassian-pm:setup"

[ -f "${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/atlassian-pm}/venv/bin/python" ] \
  && echo "  ✓  atlassian-cache: venv ready" \
  || echo "  !  atlassian-cache: venv missing (cache features degraded)"

if [ -f "${PLUGIN_ROOT}/.claude/project-config.json" ] && \
   ! grep -q "acme-corp.atlassian.net" "${PLUGIN_ROOT}/.claude/project-config.json"; then
  echo "  ✓  project-config: valid"
elif [ -f "${PLUGIN_ROOT}/.claude/project-config.json" ]; then
  echo "  ✗  project-config: placeholder values — run: /atlassian-pm:setup"
else
  echo "  ✗  project-config: file missing — run: /atlassian-pm:setup"
fi
```
