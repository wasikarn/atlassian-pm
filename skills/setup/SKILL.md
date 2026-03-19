---
name: setup
description: |
  First-time setup for atlassian-pm plugin — installs dependencies, collects Jira config,
  creates ~/.config/atlassian/.env, authenticates acli, registers mcp-atlassian, and validates.

  Idempotent: detects what is already configured and skips those steps.
  Re-running is safe — will ask before overwriting existing config.

  Triggers: "setup", "atlassian-pm setup", "/setup", "install atlassian-pm", "configure plugin"
argument-hint: ""
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# /atlassian-pm:setup

Guided first-time setup for the `atlassian-pm` plugin. Idempotent — safe to re-run.

---

## Phase 0 — Config Detection

Run as a **single Bash call** to detect current state. Sets flags used by all later phases.

```bash
# macOS guard
if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: atlassian-pm setup requires macOS (Homebrew dependency)"
  exit 1
fi

# Python 3.11+ required for jira-cache-server
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
  PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
  echo "ERROR: Python 3.11+ required (found: Python $PY_VER)"
  echo "       Install: brew install python@3.11 && brew link python@3.11"
  exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python $PY_VER ✓"

# Resolve PLUGIN_ROOT
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT=$(find "$HOME/.claude/plugins/cache/atlassian-pm/atlassian-pm" \
    -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sort -V | tail -1)
  [ -z "$PLUGIN_ROOT" ] && { echo "Error: plugin not found. Run from inside Claude Code with plugin loaded."; exit 1; }
fi

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

# project-config: exists and non-placeholder?
CONFIG_FILE="$PLUGIN_ROOT/.claude/project-config.json"
if [ -f "$CONFIG_FILE" ] && ! grep -q "acme-corp.atlassian.net" "$CONFIG_FILE"; then
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

echo "Detection complete:"
echo "  config:      $([ "$SKIP_CONFIG" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  credentials: $([ "$ENV_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  acli auth:   $([ "$ACLI_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  mcp:         $([ "$MCP_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  figma MCP:   $([ "$FIGMA_OK" = "true" ] && echo "✓ found" || echo "- not configured (optional)")"
```

**Second-run fast path:** If all four flags are true after Phase 0: skip Phases 1–4, jump to Phase 5b. The board ID lookup check in Phase 5b still applies.

```bash
if [ "$SKIP_CONFIG" = "true" ] && [ "$ENV_OK" = "true" ] && \
   [ "$ACLI_OK" = "true" ] && [ "$MCP_OK" = "true" ]; then
  echo ""
  echo "System already configured (config ✓  credentials ✓  mcp ✓)"
  echo "Running validation only..."
  # → Jump to Phase 5b (health check)
fi
```

If fast path triggered → skip Phases 1–4, jump to Phase 5b.

---

## Phase 1 — Check + Auto-install

Run as a **single Bash call**. Prints status for every dep — both installed and skipped. Skip if fast path triggered in Phase 0.

```bash
echo "Note: Phase 1 may take 1-2 minutes on first install. Safe to re-run if interrupted."
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

echo "[3/3] Syncing jira-cache-server venv..."
UV_PROJECT_ENVIRONMENT="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/atlassian-pm}/venv" \
  uv sync --project "$PLUGIN_ROOT/mcp-servers/jira-cache-server" \
  --extra embeddings --quiet \
  && echo "      venv: ready ✓" \
  || echo "      venv: sync failed (cache features degraded — core Jira ops still work)"
```

**Error handling:**

- `acli` or `uv` install fail → hard stop (both required)
- `uv sync` fail → warn + continue (cache server optional)

---

## Phase 2 — Configuration

**Skip entirely if `SKIP_CONFIG=true`.**

Ask questions in order. Each is a plain chat message.

**Required:**

1. **Jira site URL**
   - Ask: "What is your Jira site URL? (e.g. `your-company.atlassian.net`)"
   - Strip `https://` prefix if user includes it
   - Store as: `JIRA_SITE`, and set as `jira.site` + `confluence.site`

2. **Project key**
   - Ask: "What is your Jira project key? (e.g. `BEP`, `PROJ`)"
   - Validate: `^[A-Z][A-Z0-9]+$` — re-ask if invalid
   - Store as: `PROJECT_KEY` → `jira.project_key`, `SPACE_KEY` → `confluence.space_key`

3. **Board ID**
   - Ask: "What is your Jira board ID? (enter `0` if you don't know it yet — I'll help look it up after setup)"
   - Accept: positive integer (known) or `0` (unknown — defer to Phase 5b)
   - Store as: `jira.board_id` (integer)

**Optional** (via AskUserQuestion with buttons):

- Team members → `เพิ่มตอนนี้` / `ข้ามก่อน`
- Service paths → `เพิ่มตอนนี้` / `ข้ามก่อน`

---

## Phase 3 — Write Config

**Skip if `SKIP_CONFIG=true`** — print `"  config: already valid — skipping ✓"`.

**Overwrite guard:** If `project-config.json` already exists with non-placeholder values AND Phase 2 collected new values, ask:

```text
Config already exists (site: <existing>, key: <existing>).
New values: site: <new>, key: <new>
Overwrite? [y/N]:
```

- `N` (default) → use existing, set `SKIP_CONFIG=true`
- `y` → overwrite

Write config using Write tool: read `$PLUGIN_ROOT/config/project-config.json.template`, substitute collected values, write to `$PLUGIN_ROOT/.claude/project-config.json`.

---

## Phase 4 — Credentials & MCP

Three independent sub-steps. Each guarded by Phase 0 flags.

### 4a. Create `~/.config/atlassian/.env`

**Skip if `ENV_OK=true`.**

Before asking for the token, print:

```text
⚠️  Your token will be visible in this chat session.
    Clear the conversation after setup if this is a shared machine.
    Claude will never echo your token back in any output or summary.
```

Ask:

1. "What is your Atlassian email?"
2. "What is your Atlassian API token?"
   - Hint: create at `https://id.atlassian.com/manage-profile/security/api-tokens`
   - One token works for both Jira and Confluence
   - Tokens expire in ≤365 days — set a calendar reminder

**IMPORTANT:** After collecting the token, NEVER echo it back. Reference as `[token collected]` if needed.

Create directory and file:

```bash
mkdir -p ~/.config/atlassian
chmod 700 ~/.config/atlassian
echo "  Writing credentials to ~/.config/atlassian/.env ..."
```

Write file using **Write tool** (not heredoc — avoids shell expansion):

```dotenv
JIRA_URL=https://<JIRA_SITE>
JIRA_USERNAME=<EMAIL>
JIRA_API_TOKEN=<API_TOKEN>
CONFLUENCE_URL=https://<JIRA_SITE>/wiki
CONFLUENCE_USERNAME=<EMAIL>
CONFLUENCE_API_TOKEN=<API_TOKEN>
```

Then set permissions:

```bash
chmod 600 ~/.config/atlassian/.env
echo "  Credentials file written (chmod 600) ✓"
```

### 4b. Authenticate acli

**Skip if `ACLI_OK=true`.**

**Variable sourcing:** Use `EMAIL`/`API_TOKEN` from 4a if available. If `ENV_OK=true` (4a skipped):

```bash
if [ -z "$EMAIL" ]; then
  EMAIL=$(grep "^JIRA_USERNAME=" ~/.config/atlassian/.env | cut -d= -f2-)
  API_TOKEN=$(grep "^JIRA_API_TOKEN=" ~/.config/atlassian/.env | cut -d= -f2-)
fi
```

Note: `cut -d= -f2-` (not `-f2`) — Atlassian tokens are base64 and contain `=` padding.

Authenticate:

```bash
echo "${API_TOKEN}" | acli jira auth login \
  --site "${JIRA_SITE}" \
  --email "${EMAIL}" \
  --token
```

Verify via exit code:

```bash
if acli jira auth status &>/dev/null; then
  echo "  acli: authenticated ✓"
else
  echo "ERROR: acli authentication failed"
  echo "       Retry manually: echo \"\$TOKEN\" | acli jira auth login --site ${JIRA_SITE} --email ${EMAIL} --token"
  exit 1
fi
```

### 4c. Register mcp-atlassian

**Skip if `MCP_OK=true`.**

```bash
# Expand HOME at setup time — literal ~ fails in JSON args (click.Path does not expanduser)
ENV_FILE_ABS="${HOME}/.config/atlassian/.env"
# SPACE_KEY defaults to PROJECT_KEY if not separately configured
SPACE_KEY="${SPACE_KEY:-$PROJECT_KEY}"

claude mcp add --scope user mcp-atlassian -- \
  uvx --no-cache mcp-atlassian==0.21.0 \
  --env-file "${ENV_FILE_ABS}" \
  --jira-projects-filter="${PROJECT_KEY}" \
  --confluence-spaces-filter="${SPACE_KEY}"

MCP_NEWLY_ADDED=true
echo "  mcp-atlassian: registered (user scope) ✓"
```

### 4d. Configure Figma MCP (optional)

**Always runs — skip logic handled internally by `FIGMA_OK` flag.**

If `FIGMA_OK=true`, print `"  figma MCP: already configured — skipping ✓"` and skip this step.

Otherwise, ask via AskUserQuestion:

```
Would you like to configure Figma MCP for design references in skills?
(optional — skip if your team does not use Figma)
```

Buttons: `[Yes, configure]` `[Skip for now]`

If **Skip for now**: print `"  figma MCP: skipped"` and continue to Phase 5.

If **Yes, configure**:

**Step 1.** Print token visibility warning (same as Phase 4a):

```
⚠️  Your token will be visible in this chat session.
    Clear the conversation after setup if this is a shared machine.
    Claude will never echo your token back in any output or summary.
```

**Step 2.** Ask: `"What is your Figma Personal Access Token?"`

- Hint: Figma → Settings → Security → Personal Access Tokens
- **IMPORTANT:** After collecting token, NEVER echo it back. Reference as `[token collected]` if needed.

**Step 3.** Write token to env file using **Write tool** (not shell echo — avoids token in shell history):

File: `~/.config/atlassian/.figma.env`

```
FIGMA_API_KEY=<FIGMA_TOKEN>
```

**Step 4.** Set permissions and register:

```bash
chmod 600 "${HOME}/.config/atlassian/.figma.env"

claude mcp add --scope user figma -- npx -y figma-developer-mcp \
  --env-file "${HOME}/.config/atlassian/.figma.env"
```

> **Note:** `figma-developer-mcp` reads `FIGMA_API_KEY` from the env file. Token is never passed as an argv argument — consistent with Phase 4c security pattern.

**Step 5.** Verify registration:

```bash
if claude mcp get figma &>/dev/null; then
  echo "  figma MCP: registered (user scope) ✓"
  FIGMA_NEWLY_ADDED=true
else
  echo "  !  figma MCP: registration may have failed — check: claude mcp list"
fi
```

**Security properties:**

- Token written to `~/.config/atlassian/.figma.env` (chmod 600) — same directory as Jira `.env`
- Passed via `--env-file` (file path in argv, not the secret itself)
- NEVER echo token in any output, summary, or tool call

---

## Phase 5 — Finalize + Validate

### 5a. Run setup.sh

```bash
cd "$PLUGIN_ROOT" && ./scripts/setup.sh
```

Handles: git smudge/clean filter + global `~/.claude/CLAUDE.md` Atlassian block.

### 5b. Health Check

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
  && echo "  ✓  jira-cache-server: venv ready" \
  || echo "  !  jira-cache-server: venv missing (cache features degraded)"

if [ -f "${PLUGIN_ROOT}/.claude/project-config.json" ] && \
   ! grep -q "acme-corp.atlassian.net" "${PLUGIN_ROOT}/.claude/project-config.json"; then
  echo "  ✓  project-config: valid"
elif [ -f "${PLUGIN_ROOT}/.claude/project-config.json" ]; then
  echo "  ✗  project-config: placeholder values — run: /atlassian-pm:setup"
else
  echo "  ✗  project-config: file missing — run: /atlassian-pm:setup"
fi
```

**Board ID lookup (if board_id = 0):**

After the Phase 5b Bash block completes, read `project-config.json`. If `jira.board_id = 0`:

1. Print: `"Board ID is 0 (not set). MCP is now connected."`
2. Ask via AskUserQuestion: `"Look up your board ID now?"` with buttons `[Yes, look it up]` `[Skip for now]`

If **Yes, look it up**:

- Call `jira_get_agile_boards(project_key="<KEY from config>")`
- Show list of boards to user
- Ask user to pick one via AskUserQuestion
- Read `project-config.json` via Read tool, replace `jira.board_id` value with chosen integer, write back via Write tool
- Print: `"  board_id updated ✓"`

If **Skip for now**:

- Print: `"  Board ID left as 0 — doctor will warn about this"`

### 5c. Summary Output

```text
✅ atlassian-pm setup complete

  ✓  acli              authenticated
  ✓  mcp-atlassian     configured (user scope)
  ✓  jira-cache-server venv ready
  ✓  project-config    <KEY> @ <SITE>

→ /atlassian-pm:doctor    verify health at any time
→ /atlassian-pm:story-full    create your first story
→ /atlassian-pm:plan-sprint   sprint planning
```

### 5d. Restart Notice (conditional on `MCP_NEWLY_ADDED=true`)

```text
=================================================
  ACTION REQUIRED: Restart Claude Code
=================================================
  mcp-atlassian was just registered.
  Claude Code must be restarted to activate it.

  After restart, verify: /atlassian-pm:doctor
=================================================
```

---

## Error Handling Reference

| Phase | Error | Action |
| --- | --- | --- |
| 0 | Not macOS | Hard stop: `ERROR: requires macOS` |
| 0 | Python < 3.11 | Hard stop: show `brew install python@3.11` command |
| 0 | Plugin not found | Hard stop: `Error: plugin not found` |
| 1 | acli install fail | Hard stop: show brew command |
| 1 | uv install fail | Hard stop: show brew command |
| 1 | uv sync fail | Warn + continue: note cache degraded |
| 2 | Invalid project key | Re-ask with format reminder |
| 3 | Write permission denied | Hard stop: check directory permissions |
| 4b | acli auth fail | Hard stop: show retry command |
| 5 | setup.sh fail | Show error output, suggest manual run |
