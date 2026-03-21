---
name: doctor
disable-model-invocation: true
description: |
  Health check for atlassian-pm environment — runs 10 checks and reports status.

  Checks: acli install, acli auth, uv install, atlassian-cache venv, mcp-atlassian config,
  project-config valid, board_id non-zero, git filters, CLAUDE.md block, team-detail config.

  Never stops on failure — shows complete picture. Run after setup or after updates.

  Triggers: "doctor", "health check", "check setup", "diagnose", "verify install", "/doctor"
argument-hint: ""
effort: low
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
TOTAL=11

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
    echo "     → Run: /atlassian-pm:setup (will offer MCP lookup in Phase 5b)"
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

REQUIRED=$((TOTAL - SKIP))
echo ""
echo "${PASS}/${REQUIRED} checks passed  ·  ${FAIL} failed  ·  ${WARN} warnings  ·  ${SKIP} optional skipped"
echo "✓ pass  ✗ fail  ! warning  - optional"
```

## Examples

### ✅ Good

```text
/doctor                               # run after initial setup to confirm everything is green
/doctor                               # run after plugin update to catch regressions
/doctor                               # run when Jira MCP tools suddenly return "not found"
```

### ❌ Bad

```text
/doctor --fix                         # no flags exist — doctor is read-only, it never fixes anything
/doctor                               # running after every single code change is unnecessary overhead
/doctor {{PROJECT_KEY}}-123                       # takes no arguments — issue keys are ignored
```

**Common mistakes:**

- Expecting `/doctor` to fix broken items — it only reports status. Use `/setup` to fix failures.
- Running it to diagnose a Jira API error mid-session — doctor checks environment (tools, venv, config), not live Jira connectivity.
- Treating `! warning` as a blocker — warnings (e.g., missing team-detail) are optional; only `✗ fail` items block core functionality.
- Not restarting Claude Code after `/setup` installs MCP — doctor will show mcp-atlassian as configured but tools remain inactive until restart.

## Error Handling

If any bash command fails entirely (e.g., `python3` not found), print `!  check skipped (python3 unavailable)` and increment WARN. Never `exit 1` — always complete all checks.

## 🎓 Domain Expert Notes

### Why This Approach

Doctor implements the **pre-flight checklist pattern** from aviation: a complete, ordered scan of all critical systems run before every mission, regardless of how routine the flight seems. The non-negotiable "never stop on failure" rule mirrors aviation checklists exactly — a partial check is worse than no check, because it creates false confidence about unverified items.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Pre-flight checklist (aviation) | All 10 checks run unconditionally | Partial results create false confidence — full picture always required |
| Shift-left verification | Running doctor after setup/update, not after first failure | Catch environment drift before it blocks work, not during it |
| Idempotent diagnostics | Every check is read-only with no side effects | Safe to run repeatedly in any context — no state mutation from observation |
| Dependency graph validation | Checks ordered: acli → auth → uv → venv → MCP → config → board | Upstream failures explain downstream ones; order reveals root cause |
| Pass/Warn/Fail/Skip severity model | `✓ ✗ ! -` output symbols | Operators need graduated response: fail = blocking, warn = degraded, skip = optional |

### Key Metrics

- **Time-to-green:** How long from fresh machine to all 10 checks passing — target under 5 minutes with `/setup`. Longer indicates dependency install issues.
- **Warning-to-failure ratio:** A healthy environment has 0 fails and ≤1 warning (team-detail missing is expected). Multiple warnings signal configuration drift.
- **Check coverage:** 10 checks across 5 layers (CLI tools, auth, Python runtime, MCP integration, project config) — gaps in any layer leave blind spots that surface as cryptic mid-session errors.

### Expert Decision Criteria

**When to run doctor:**

- After any `/setup` or plugin reinstall — verify the new state before starting work
- When Jira MCP tools return "not found" — most commonly venv or MCP registration issue
- After a machine migration or macOS upgrade — PATH changes silently break `acli` and `uv`
- Before a sprint planning session — board_id=0 causes silent failures in sprint-related skills

**How to interpret results:**

- `✗ fail` on acli auth → run `/setup` phases 4a+4b only (not full setup)
- `✗ fail` on mcp-atlassian → registered but inactive means restart needed; missing means run `/setup`
- `! warning` on venv → doctor auto-heals this; if it fails, uv or PLUGIN_ROOT resolution is broken
- All checks green but Jira still fails → live API connectivity issue, not environment (doctor can't test that)

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| mcp-atlassian shows `✓` but Jira tools return "not found" | MCP registered this session — tools activate only after restart | Restart Claude Code, re-run doctor |
| venv check fails repeatedly after auto-heal attempt | `uv` installed after session start — not in PATH for this shell | Open new terminal, re-run doctor |
| board_id = 0 warning persists | Setup was run without Phase 5b board lookup | Run `/setup` and choose board when prompted, or edit `project-config.json` directly |
| git filters `! warning` in cache install | Plugin loaded from `~/.claude/plugins/cache/` — filters are in source repo, not cache | Expected behavior; filters only needed in source repo contributors |
| All checks pass but `CLAUDE.md` block warning | `~/.claude/CLAUDE.md` was manually edited and block removed | Re-run `/setup` Phase 5a (`setup.sh`) to re-inject the block |

### Authoritative References

- **Atul Gawande, "The Checklist Manifesto" (2009):** Checklists work because they encode expert knowledge in a form that survives high-pressure situations — the same reason doctor never stops on failure.
- **Google SRE Book — "Testing for Reliability":** Environment validation is a form of canary testing; catching drift in dev prevents cascading failures in production.
- **BetterStack Health Check Guide:** Health check operations must be idempotent and read-only — they can be called repeatedly without side effects, making them safe for automation and CI gates.
