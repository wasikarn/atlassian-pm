---
name: apm-doctor
description: |
  Health check for atlassian-pm environment — runs 12 checks and reports status.

  Checks: acli install, acli auth, uv install, atlassian-cache venv, mcp-atlassian config,
  project-config valid, board_id non-zero, git filters, CLAUDE.md block, team-detail config.

  Never stops on failure — shows complete picture. Run after setup or after updates.

  Triggers: "apm doctor", "atlassian-pm health check", "check apm setup", "diagnose atlassian", "/apm-doctor", "ตรวจสอบ apm setup"
  Use when: verifying plugin health and configuration after setup or after issues arise
  Do NOT use for: initial setup (use apm-setup); creating issues (use create-epic or create-task)
x-compatibility: []
argument-hint: ""
effort: low
allowed-tools: Bash
---

# /atlassian-pm:apm-doctor

Health check for the `atlassian-pm` environment. Runs all 12 checks regardless of failures.

## Instructions

Run all checks as a **single Bash call**. Never stop mid-run. Collect all results and print the final report.

```bash
# Resolve PLUGIN_ROOT
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT=$(find "$HOME/.claude/plugins/cache/atlassian-pm/atlassian-pm" \
    -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sort -V | tail -1)
fi

PASS=0
WARN=0
FAIL=0
SKIP=0
TOTAL=12

echo "Checking atlassian-pm environment..."
echo ""

# Check 1: acli installed
if command -v acli &>/dev/null; then
  VER=$(acli --version 2>/dev/null | head -1 || echo "unknown")
  echo "  ✓  acli installed ($VER)"
  PASS=$((PASS+1))
else
  echo "  ✗  acli not found"
  echo "     → Install: brew tap atlassian/homebrew-acli && brew install acli"
  FAIL=$((FAIL+1))
fi

# Check 2: acli authenticated
AUTH_OUTPUT=$(acli jira auth status 2>/dev/null)
AUTH_EXIT=$?
if [ $AUTH_EXIT -eq 0 ]; then
  SITE=$(echo "$AUTH_OUTPUT" | grep "Site:" | awk '{print $2}')
  echo "  ✓  acli authenticated (${SITE:-unknown site})"
  PASS=$((PASS+1))
else
  echo "  ✗  acli not authenticated"
  echo "     → Run: /atlassian-pm:setup"
  FAIL=$((FAIL+1))
fi

# Check 3: uv installed
if command -v uv &>/dev/null; then
  VER=$(uv --version 2>/dev/null | head -1 || echo "unknown")
  echo "  ✓  uv installed ($VER)"
  PASS=$((PASS+1))
else
  echo "  ✗  uv not found"
  echo "     → Install: brew install uv"
  FAIL=$((FAIL+1))
fi

# Check 4: atlassian-cache venv
# Data dir name is always "{plugin_name}-{marketplace_name}" = "atlassian-pm-atlassian-pm"
DATA_DIR="$HOME/.claude/plugins/data/atlassian-pm-atlassian-pm"
VENV_PYTHON="$DATA_DIR/venv/bin/python"
if [ -f "$VENV_PYTHON" ]; then
  echo "  ✓  atlassian-cache venv ready"
  PASS=$((PASS+1))
elif command -v uv &>/dev/null && [ -n "$PLUGIN_ROOT" ]; then
  echo "  ~  atlassian-cache venv missing — recreating..."
  mkdir -p "$DATA_DIR"
  if uv venv "$DATA_DIR/venv" --quiet 2>/dev/null && \
     uv pip install --python "$DATA_DIR/venv/bin/python" \
       "$PLUGIN_ROOT/mcp-servers/atlassian-cache" --quiet 2>/dev/null; then
    echo "  ✓  atlassian-cache venv recreated"
    PASS=$((PASS+1))
  else
    echo "  ✗  atlassian-cache venv recreation failed"
    echo "     → Run: /atlassian-pm:setup"
    FAIL=$((FAIL+1))
  fi
else
  echo "  !  atlassian-cache venv missing (cache features degraded)"
  echo "     → Run: /atlassian-pm:setup"
  WARN=$((WARN+1))
fi

# Check 4b: atlassian-cache in .mcp.json
MCP_JSON="${PLUGIN_ROOT}/.mcp.json"
if [ -f "$MCP_JSON" ] && python3 -c "import json; d=json.load(open('$MCP_JSON')); exit(0 if 'atlassian-cache' in d.get('mcpServers', {}) else 1)" 2>/dev/null; then
  echo "  ✓  atlassian-cache configured in .mcp.json"
  PASS=$((PASS+1))
else
  echo "  !  atlassian-cache missing from .mcp.json (cache tools unavailable)"
  echo "     → Plugin may be outdated — reinstall: /plugin install atlassian-pm@atlassian-pm"
  WARN=$((WARN+1))
fi

# Check 5: mcp-atlassian configured
if claude mcp get mcp-atlassian &>/dev/null; then
  echo "  ✓  mcp-atlassian configured (user scope)"
  echo "     (if Jira tools show 'not found', restart Claude Code to activate)"
  PASS=$((PASS+1))
else
  echo "  ✗  mcp-atlassian not registered"
  echo "     → Run: /atlassian-pm:setup"
  FAIL=$((FAIL+1))
fi

# Check 6: project-config valid (non-placeholder)
CONFIG_FILE="${PLUGIN_ROOT}/.claude/project-config.json"
BACKUP_CONFIG="$HOME/.config/atlassian/project-config.json"
# Auto-restore from backup if config is missing (e.g. after clean install)
if [ ! -f "$CONFIG_FILE" ] && [ -f "$BACKUP_CONFIG" ]; then
  cp "$BACKUP_CONFIG" "$CONFIG_FILE"
  echo "  ✓  project-config restored from backup (~/.config/atlassian/project-config.json)"
fi
if [ -f "$CONFIG_FILE" ] && ! grep -qE "YOUR-INSTANCE|YOUR_PROJECT_KEY|acme-corp\.atlassian\.net" "$CONFIG_FILE"; then
  SITE=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['jira']['site'])" 2>/dev/null || echo "?")
  KEY=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['jira']['project_key'])" 2>/dev/null || echo "?")
  echo "  ✓  project-config valid ($KEY @ $SITE)"
  PASS=$((PASS+1))
else
  echo "  ✗  project-config missing or has placeholder values"
  echo "     → Run: /atlassian-pm:setup"
  FAIL=$((FAIL+1))
fi

# Check 7: board_id non-zero
if [ -f "$CONFIG_FILE" ]; then
  BOARD_ID=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); v=c['jira']['board_id']; print(v if v else 0)" 2>/dev/null || echo "0")
  if [ "$BOARD_ID" != "0" ] && [ -n "$BOARD_ID" ]; then
    echo "  ✓  board_id = $BOARD_ID"
    PASS=$((PASS+1))
  else
    echo "  !  board_id = 0 (placeholder)"
    echo "     → Run: /atlassian-pm:setup (will offer MCP lookup in Phase 6 step 2)"
    WARN=$((WARN+1))
  fi
else
  echo "  !  board_id check skipped (no config file)"
  WARN=$((WARN+1))
fi

# Check 8: git filters configured
# Skip when running from plugin cache (not a git repo — expected for cache installs)
_IS_CACHE_INSTALL=false
[[ "$PLUGIN_ROOT" == *"/.claude/plugins/cache/"* ]] && _IS_CACHE_INSTALL=true

if [ -n "$PLUGIN_ROOT" ] && git -C "$PLUGIN_ROOT" config --get filter.project-config.smudge &>/dev/null; then
  echo "  ✓  git filters configured (smudge/clean)"
  PASS=$((PASS+1))
elif [ "$_IS_CACHE_INSTALL" = true ]; then
  echo "  ✓  git filters n/a (cache install — filters live in source repo)"
  PASS=$((PASS+1))
else
  echo "  !  git filters not configured"
  if [ -n "$PLUGIN_ROOT" ]; then
    echo "     → Run: cd $PLUGIN_ROOT && ./scripts/setup.sh"
  else
    echo "     → Run: /atlassian-pm:setup (plugin root not resolved)"
  fi
  WARN=$((WARN+1))
fi

# Check 9: CLAUDE.md Atlassian block
if grep -q "Atlassian Settings" "$HOME/.claude/CLAUDE.md" 2>/dev/null; then
  echo "  ✓  CLAUDE.md Atlassian block present"
  PASS=$((PASS+1))
else
  echo "  !  CLAUDE.md missing Atlassian Settings block"
  echo "     → Run: /atlassian-pm:setup"
  WARN=$((WARN+1))
fi

# Check 10: team-detail config (optional — auto-scaffold from template)
TEAM_DETAIL="${PLUGIN_ROOT}/.claude/project-config-team-detail.json"
TEAM_TEMPLATE="${PLUGIN_ROOT}/.claude/project-config-team-detail.json.template"
if [ -f "$TEAM_DETAIL" ]; then
  echo "  ✓  project-config-team-detail.json present"
  PASS=$((PASS+1))
elif [ -f "$TEAM_TEMPLATE" ]; then
  cp "$TEAM_TEMPLATE" "$TEAM_DETAIL"
  echo "  ~  project-config-team-detail.json scaffolded from template"
  echo "     → Edit $TEAM_DETAIL to add real git evidence and capacity data"
  echo "     → Run /atlassian-pm:velocity-tracker to populate velocity history"
  WARN=$((WARN+1))
else
  echo "  -  project-config-team-detail.json not found (no template to scaffold from)"
  echo "     (optional — needed for sprint planning only)"
  SKIP=$((SKIP+1))
fi

# Check 11: board_monitor daemon (optional — proactive intelligence)
MONITOR_PLIST="$HOME/Library/LaunchAgents/com.atlassian-pm.monitor.plist"
if launchctl list com.atlassian-pm.monitor &>/dev/null; then
  echo "  ✓  board_monitor daemon running"
  PASS=$((PASS+1))
elif [ -f "$MONITOR_PLIST" ]; then
  echo "  !  board_monitor plist exists but daemon not loaded"
  echo "     → Run: launchctl bootstrap gui/$(id -u) $MONITOR_PLIST"
  WARN=$((WARN+1))
else
  echo "  -  board_monitor daemon not installed (optional — proactive intelligence)"
  if [ -n "${PLUGIN_ROOT:-}" ]; then
    echo "     → Install: $PLUGIN_ROOT/scripts/setup_monitor.sh"
  else
    echo "     → Install: scripts/setup_monitor.sh (set CLAUDE_PLUGIN_ROOT first)"
  fi
  SKIP=$((SKIP+1))
fi

REQUIRED=$((TOTAL - SKIP))
echo ""
echo "${PASS}/${REQUIRED} checks passed  ·  ${FAIL} failed  ·  ${WARN} warnings  ·  ${SKIP} optional skipped"
echo "✓ pass  ✗ fail  ! warning  - optional"
```

## Examples

```text
/doctor          # run after initial setup or plugin update to confirm green
/doctor          # run when Jira MCP tools suddenly return "not found"
```

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

No shared reference dependencies — all checks performed via Bash commands only.
