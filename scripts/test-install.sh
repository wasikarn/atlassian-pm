#!/usr/bin/env bash
# test-install.sh — Full install cycle test for atlassian-pm plugin
#
# Usage:
#   ./scripts/test-install.sh            # full test: remove → install → setup sim → doctor
#   ./scripts/test-install.sh --doctor   # doctor only (skip remove/install)
#   ./scripts/test-install.sh --no-reinstall  # setup sim + doctor only (skip remove/install)
#
# Exit code: 0 = all pass, 1 = one or more failures

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── color helpers ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}✓${NC}  $*"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}✗${NC}  $*"; FAIL=$((FAIL+1)); }
warn() { echo -e "  ${YELLOW}!${NC}  $*"; WARN=$((WARN+1)); }
info() { echo -e "  ${CYAN}→${NC}  $*"; }

PASS=0; FAIL=0; WARN=0
MODE="${1:-}"

# ── resolve paths ──────────────────────────────────────────────────────────────
_get_plugin_root() {
  find "$HOME/.claude/plugins/cache/atlassian-pm/atlassian-pm" \
    -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sort -V | tail -1
}
_get_plugin_data() {
  echo "$HOME/.claude/plugins/data/atlassian-pm-atlassian-pm"
}
_is_placeholder() {
  grep -qE "acme-corp\.atlassian\.net|YOUR-INSTANCE|YOUR_PROJECT_KEY" "$1" 2>/dev/null
}

# ── phase 1: remove + install ─────────────────────────────────────────────────
if [[ "$MODE" != "--doctor" && "$MODE" != "--no-reinstall" ]]; then
  echo ""
  echo -e "${CYAN}━━━ Phase 1: Remove + Install ━━━${NC}"

  info "Removing plugin..."
  if claude plugin remove atlassian-pm@atlassian-pm 2>&1 | grep -q "Successfully uninstalled"; then
    pass "Plugin removed"
  else
    warn "Plugin was not installed (fresh machine?)"
  fi

  info "Checking post-remove state..."
  PLUGIN_DATA=$(_get_plugin_data)
  if [ ! -f "${PLUGIN_DATA}/venv/bin/python" ]; then
    pass "venv wiped on remove (expected)"
  else
    warn "venv still present after remove (unexpected)"
  fi
  if [ -f "$HOME/.config/atlassian/project-config.json" ]; then
    pass "config backup survived remove"
  else
    warn "no config backup at ~/.config/atlassian/project-config.json (new user?)"
  fi

  info "Installing plugin..."
  if claude plugin install atlassian-pm@atlassian-pm 2>&1 | grep -q "Successfully installed"; then
    pass "Plugin installed"
  else
    fail "Plugin install FAILED"
    echo -e "\n${RED}Aborting — install failed${NC}"
    exit 1
  fi

  VERSION=$(claude plugin list 2>&1 | grep -A2 "atlassian-pm@atlassian-pm" | grep "Version:" | awk '{print $2}')
  pass "Installed version: ${VERSION}"

  PLUGIN_ROOT=$(_get_plugin_root)
  if [ -n "$PLUGIN_ROOT" ]; then
    pass "Cache dir: $PLUGIN_ROOT"
  else
    fail "Plugin cache directory not found"
    exit 1
  fi

  info "Checking post-install state..."
  CONFIG_IN_CACHE="${PLUGIN_ROOT}/.claude/project-config.json"
  if [ ! -f "$CONFIG_IN_CACHE" ] || _is_placeholder "$CONFIG_IN_CACHE"; then
    pass "Config missing/placeholder in cache (expected — will be restored by setup)"
  else
    warn "Config already has real values in cache (was bump-version.sh copy still active?)"
  fi
  if [ ! -f "${PLUGIN_DATA}/venv/bin/python" ]; then
    pass "venv missing after install (expected — setup will recreate)"
  else
    warn "venv already present after install (stale?)"
  fi
fi

# ── phase 2: setup simulation ──────────────────────────────────────────────────
if [[ "$MODE" != "--doctor" ]]; then
  echo ""
  echo -e "${CYAN}━━━ Phase 2: Setup Simulation (/atlassian-pm:setup) ━━━${NC}"

  PLUGIN_ROOT=$(_get_plugin_root)
  PLUGIN_DATA=$(_get_plugin_data)
  CONFIG_FILE="${PLUGIN_ROOT}/.claude/project-config.json"
  CONFIG_BACKUP="$HOME/.config/atlassian/project-config.json"
  TEAM_DETAIL="${PLUGIN_ROOT}/.claude/project-config-team-detail.json"
  TEAM_DETAIL_TMPL="${PLUGIN_ROOT}/.claude/project-config-team-detail.json.template"

  # Phase 0: auto-restore
  info "Phase 0: auto-restore config..."
  if [ ! -f "$CONFIG_FILE" ] || _is_placeholder "$CONFIG_FILE"; then
    if [ -f "$CONFIG_BACKUP" ] && ! _is_placeholder "$CONFIG_BACKUP"; then
      cp "$CONFIG_BACKUP" "$CONFIG_FILE"
      pass "project-config.json restored from backup"
    else
      warn "No backup found — new user must configure manually (expected for fresh machine)"
    fi
  else
    pass "Config already valid — restore skipped"
  fi

  # Phase 0: flag detection
  info "Phase 0: flag detection..."
  SKIP_CONFIG=false; ENV_OK=false; ACLI_OK=false; MCP_OK=false; VENV_OK=false
  [ -f "$CONFIG_FILE" ] && ! _is_placeholder "$CONFIG_FILE" && SKIP_CONFIG=true
  [ -f "$HOME/.config/atlassian/.env" ] && grep -Eq "^JIRA_API_TOKEN=.+" "$HOME/.config/atlassian/.env" && ENV_OK=true
  acli jira auth status &>/dev/null && ACLI_OK=true
  claude mcp get mcp-atlassian &>/dev/null && MCP_OK=true
  [ -f "${PLUGIN_DATA}/venv/bin/python" ] && VENV_OK=true

  [ "$SKIP_CONFIG" = "true" ] && pass "config flag: true" || warn "config flag: false (new user → Phase 2 would collect config)"
  [ "$ENV_OK" = "true" ] && pass ".env flag: true" || warn ".env flag: false (Phase 4a would create it)"
  [ "$ACLI_OK" = "true" ] && pass "acli auth flag: true" || warn "acli auth flag: false (Phase 4b would authenticate)"
  [ "$MCP_OK" = "true" ] && pass "mcp flag: true" || warn "mcp flag: false (Phase 4c would register)"
  [ "$VENV_OK" = "true" ] && pass "venv flag: true — fast path" || info "venv flag: false → Phase 1 will run"

  # Phase 1: uv sync (only if venv missing)
  if [ "$VENV_OK" = "false" ]; then
    info "Phase 1: uv sync venv..."
    if UV_PROJECT_ENVIRONMENT="${PLUGIN_DATA}/venv" \
        uv sync --project "${PLUGIN_ROOT}/mcp-servers/jira-cache-server" \
        --extra embeddings --quiet 2>&1; then
      pass "venv synced ✓"
    else
      fail "uv sync FAILED"
    fi
  fi

  # Phase 5a: team-detail
  info "Phase 5a: team-detail..."
  if [ ! -f "$TEAM_DETAIL" ] && [ -f "$TEAM_DETAIL_TMPL" ]; then
    cp "$TEAM_DETAIL_TMPL" "$TEAM_DETAIL"
    pass "team-detail created from template"
  else
    pass "team-detail already exists"
  fi

  # Verify final cache state
  info "Verifying .claude/ contents..."
  for f in project-config.json project-config-team-detail.json; do
    if [ -f "${PLUGIN_ROOT}/.claude/$f" ]; then
      pass "$f present"
    else
      fail "$f MISSING"
    fi
  done
  if [ -f "${PLUGIN_DATA}/venv/bin/python" ]; then
    pass "venv/bin/python present"
  else
    fail "venv MISSING after setup"
  fi
fi

# ── phase 3: doctor (11 checks) ───────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ Phase 3: Doctor (11 checks) ━━━${NC}"

PLUGIN_ROOT=$(_get_plugin_root)
PLUGIN_DATA=$(_get_plugin_data)
CONFIG_FILE="${PLUGIN_ROOT}/.claude/project-config.json"
DR_PASS=0; DR_FAIL=0; DR_WARN=0; DR_SKIP=0; DR_TOTAL=11

_dr_pass() { echo -e "  ${GREEN}✓${NC}  $*"; DR_PASS=$((DR_PASS+1)); }
_dr_fail() { echo -e "  ${RED}✗${NC}  $*"; DR_FAIL=$((DR_FAIL+1)); }
_dr_warn() { echo -e "  ${YELLOW}!${NC}  $*"; DR_WARN=$((DR_WARN+1)); }

# 1 acli
command -v acli &>/dev/null && _dr_pass "acli installed ($(acli --version 2>/dev/null | head -1))" || _dr_fail "acli not found"
# 2 acli auth
acli jira auth status &>/dev/null && _dr_pass "acli authenticated ($(acli jira auth status 2>/dev/null | grep Site: | awk '{print $2}'))" || _dr_fail "acli not authenticated"
# 3 uv
command -v uv &>/dev/null && _dr_pass "uv installed ($(uv --version 2>/dev/null | head -1))" || _dr_fail "uv not found"
# 4 venv
if [ -f "${PLUGIN_DATA}/venv/bin/python" ]; then
  _dr_pass "jira-cache-server venv ready"
elif command -v uv &>/dev/null && [ -n "$PLUGIN_ROOT" ]; then
  echo -e "  ${CYAN}~${NC}  jira-cache-server venv missing — recreating..."
  mkdir -p "$PLUGIN_DATA"
  if uv venv "$PLUGIN_DATA/venv" --quiet 2>/dev/null && \
     uv pip install --python "$PLUGIN_DATA/venv/bin/python" \
       "$PLUGIN_ROOT/mcp-servers/jira-cache-server" --quiet 2>/dev/null; then
    _dr_pass "jira-cache-server venv recreated"
  else
    _dr_fail "jira-cache-server venv recreation failed → run /atlassian-pm:setup"
  fi
else
  _dr_warn "jira-cache-server venv missing → run /atlassian-pm:setup"
fi
# 4b .mcp.json
python3 -c "import json; d=json.load(open('$PLUGIN_ROOT/.mcp.json')); exit(0 if 'jira-cache-server' in d.get('mcpServers',{}) else 1)" 2>/dev/null \
  && _dr_pass "jira-cache-server in .mcp.json" || _dr_warn "jira-cache-server missing from .mcp.json"
# 5 mcp-atlassian
claude mcp get mcp-atlassian &>/dev/null && _dr_pass "mcp-atlassian configured" || _dr_fail "mcp-atlassian not registered"
# 6 project-config
if [ -f "$CONFIG_FILE" ] && ! _is_placeholder "$CONFIG_FILE"; then
  K=$(python3 -c "import json;print(json.load(open('$CONFIG_FILE'))['jira']['project_key'])" 2>/dev/null || echo "?")
  S=$(python3 -c "import json;print(json.load(open('$CONFIG_FILE'))['jira']['site'])" 2>/dev/null || echo "?")
  _dr_pass "project-config valid ($K @ $S)"
else
  _dr_fail "project-config missing/placeholder"
fi
# 7 board_id
B=$(python3 -c "import json;print(json.load(open('$CONFIG_FILE'))['jira']['board_id'])" 2>/dev/null || echo 0)
[ "$B" != "0" ] && [ -n "$B" ] && _dr_pass "board_id = $B" || _dr_warn "board_id = 0 (run /atlassian-pm:setup Phase 5b)"
# 8 git filters
[[ "$PLUGIN_ROOT" == *"/.claude/plugins/cache/"* ]] && _dr_pass "git filters n/a (cache install)" || _dr_warn "git filters not configured"
# 9 CLAUDE.md
grep -q "Atlassian Settings" "$HOME/.claude/CLAUDE.md" 2>/dev/null && _dr_pass "CLAUDE.md Atlassian block present" || _dr_warn "CLAUDE.md missing Atlassian block"
# 10 team-detail (optional)
if [ -f "${PLUGIN_ROOT}/.claude/project-config-team-detail.json" ]; then
  _dr_pass "project-config-team-detail.json present"
else
  echo -e "  -  project-config-team-detail.json not found (optional — needed for sprint planning only)"
  DR_SKIP=$((DR_SKIP+1))
fi

# ── summary ───────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────"
echo ""
DR_REQUIRED=$((DR_TOTAL - DR_SKIP))
echo -e "  Doctor:    ${DR_PASS}/${DR_REQUIRED} passed  ·  ${DR_FAIL} failed  ·  ${DR_WARN} warnings  ·  ${DR_SKIP} optional skipped"
echo -e "  Pipeline:  ${PASS} passed  ·  ${FAIL} failed  ·  ${WARN} warnings"
echo ""

TOTAL_FAIL=$((FAIL + DR_FAIL))
TOTAL_WARN=$((WARN + DR_WARN))

if [ "$TOTAL_FAIL" -eq 0 ] && [ "$TOTAL_WARN" -eq 0 ]; then
  echo -e "  ${GREEN}✅ ALL PASS — install flow 100% clean${NC}"
else
  echo -e "  ${YELLOW}⚠️  PASS with ${TOTAL_WARN} warning(s)${NC}"
fi

# Warn if installed version differs from session's CLAUDE_PLUGIN_ROOT
SESSION_VER=""
[[ "${CLAUDE_PLUGIN_ROOT:-}" =~ /([0-9]+\.[0-9]+\.[0-9]+)$ ]] && SESSION_VER="${BASH_REMATCH[1]}"
if [ -n "$SESSION_VER" ] && [ "$SESSION_VER" != "${VERSION:-}" ]; then
  echo ""
  echo -e "  ${YELLOW}⚠️  RESTART REQUIRED${NC}"
  echo -e "     Session CLAUDE_PLUGIN_ROOT = v${SESSION_VER}, installed = v${VERSION:-?}"
  echo -e "     Hook errors will appear until Claude Code is restarted."
fi
echo ""

[ "$TOTAL_FAIL" -eq 0 ] && exit 0 || exit 1
