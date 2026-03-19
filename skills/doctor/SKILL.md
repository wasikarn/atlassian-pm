---
name: doctor
description: |
  Health check for atlassian-pm environment — runs 10 checks and reports status.

  Checks: acli install, acli auth, uv install, jira-cache-server venv, mcp-atlassian config,
  project-config valid, board_id non-zero, git filters, CLAUDE.md block, team-detail config.

  Never stops on failure — shows complete picture. Run after setup or after updates.

  Triggers: "doctor", "health check", "check setup", "diagnose", "verify install", "/doctor"
argument-hint: ""
allowed-tools: Bash
---

# /atlassian-pm:doctor

Health check for the `atlassian-pm` environment. Runs all 10 checks regardless of failures.

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
TOTAL=10

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

# Check 4: jira-cache-server venv
VENV_PYTHON="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/atlassian-pm}/venv/bin/python"
if [ -f "$VENV_PYTHON" ]; then
  echo "  ✓  jira-cache-server venv ready"
  PASS=$((PASS+1))
else
  echo "  !  jira-cache-server venv missing (cache features degraded)"
  echo "     → Run: /atlassian-pm:setup"
  WARN=$((WARN+1))
fi

# Check 5: mcp-atlassian configured
if claude mcp get mcp-atlassian &>/dev/null; then
  echo "  ✓  mcp-atlassian configured (user scope)"
  PASS=$((PASS+1))
else
  echo "  ✗  mcp-atlassian not registered"
  echo "     → Run: /atlassian-pm:setup"
  FAIL=$((FAIL+1))
fi

# Check 6: project-config valid (non-placeholder)
CONFIG_FILE="${PLUGIN_ROOT}/.claude/project-config.json"
if [ -f "$CONFIG_FILE" ] && ! grep -q "acme-corp.atlassian.net" "$CONFIG_FILE"; then
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
    echo "     → Run: /atlassian-pm:setup to set correct board ID"
    WARN=$((WARN+1))
  fi
else
  echo "  !  board_id check skipped (no config file)"
  WARN=$((WARN+1))
fi

# Check 8: git filters configured
if [ -n "$PLUGIN_ROOT" ] && git -C "$PLUGIN_ROOT" config --get filter.project-config.smudge &>/dev/null; then
  echo "  ✓  git filters configured (smudge/clean)"
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

# Check 10: team-detail config (optional)
TEAM_DETAIL="${PLUGIN_ROOT}/.claude/project-config-team-detail.json"
if [ -f "$TEAM_DETAIL" ]; then
  echo "  ✓  project-config-team-detail.json present"
  PASS=$((PASS+1))
else
  echo "  -  project-config-team-detail.json not found"
  echo "     (optional — needed for sprint planning only)"
  SKIP=$((SKIP+1))
fi

echo ""
echo "${PASS}/${TOTAL} checks passed  ·  ${FAIL} failed  ·  ${WARN} warnings"
echo "✓ pass  ✗ fail  ! warning  - optional"
```

## Error Handling

If any bash command fails entirely (e.g., `python3` not found), print `!  check skipped (python3 unavailable)` and increment WARN. Never `exit 1` — always complete all checks.
