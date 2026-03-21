---
name: setup
disable-model-invocation: true
description: |
  First-time setup for atlassian-pm plugin — installs dependencies, collects Jira config,
  creates ~/.config/atlassian/.env, authenticates acli, registers mcp-atlassian, and validates.

  Idempotent: detects what is already configured and skips those steps.
  Re-running is safe — will ask before overwriting existing config.

  Triggers: "setup", "atlassian-pm setup", "/setup", "install atlassian-pm", "configure plugin"
argument-hint: ""
effort: low
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

# Python 3.11+ required for atlassian-cache
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

echo "Detection complete:"
echo "  config:      $([ "$SKIP_CONFIG" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  credentials: $([ "$ENV_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  acli auth:   $([ "$ACLI_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  mcp:         $([ "$MCP_OK" = "true" ] && echo "✓ found" || echo "✗ needed")"
echo "  venv:        $([ "$VENV_OK" = "true" ] && echo "✓ found" || echo "✗ needed (will sync)")"
echo "  figma MCP:   $([ "$FIGMA_OK" = "true" ] && echo "✓ found" || echo "- not configured (optional)")"
```

**Second-run fast path:** If all five flags are true after Phase 0: skip Phases 1–4, jump to Phase 5b. The venv check ensures Phase 1 always runs when venv is missing (e.g. after plugin reinstall).

```bash
if [ "$SKIP_CONFIG" = "true" ] && [ "$ENV_OK" = "true" ] && \
   [ "$ACLI_OK" = "true" ] && [ "$MCP_OK" = "true" ] && [ "$VENV_OK" = "true" ]; then
  echo ""
  echo "System already configured (config ✓  credentials ✓  mcp ✓  venv ✓)"
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
   - Ask: "What is your Jira project key? (e.g. `{{PROJECT_KEY}}`, `PROJ`)"
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

After writing, backup config so it survives future plugin reinstalls:

```bash
mkdir -p "$HOME/.config/atlassian"
cp "$PLUGIN_ROOT/.claude/project-config.json" "$HOME/.config/atlassian/atlassian-pm-config.json"
echo "  → Config backed up to ~/.config/atlassian/ ✓"
```

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

---

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
# Copy team-detail config from template if missing
TEAM_DETAIL="$PLUGIN_ROOT/.claude/project-config-team-detail.json"
TEAM_DETAIL_TEMPLATE="$PLUGIN_ROOT/.claude/project-config-team-detail.json.template"

if [ ! -f "$TEAM_DETAIL" ]; then
  if [ -f "$TEAM_DETAIL_TEMPLATE" ]; then
    cp "$TEAM_DETAIL_TEMPLATE" "$TEAM_DETAIL"
    echo "  ✓  project-config-team-detail.json created from template"
    echo "     Edit this file to add real team velocity and capacity data"
    echo "     Required for: /atlassian-pm:plan-sprint"
  else
    echo "  !  project-config-team-detail.json template not found"
    echo "     Create manually from: .claude/project-config-team-detail.json.template"
  fi
else
  echo "  ✓  project-config-team-detail.json already exists"
fi

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
  ✓  atlassian-cache venv ready
  ✓  project-config    <KEY> @ <SITE>

→ /atlassian-pm:doctor    verify health at any time
→ /atlassian-pm:create-story  create your first story
→ /atlassian-pm:plan-sprint   sprint planning
```

### 5d. Restart Notice (conditional on `MCP_NEWLY_ADDED=true` OR `FIGMA_NEWLY_ADDED=true`)

Print this notice if `MCP_NEWLY_ADDED=true` OR `FIGMA_NEWLY_ADDED=true`.

```text
=================================================
  ⚠️  ACTION REQUIRED: Restart Claude Code NOW
=================================================
  The following MCP servers were registered this session:
  - mcp-atlassian (Jira + Confluence tools)
  [Print this line only if FIGMA_NEWLY_ADDED=true: - figma (design references)]

  These tools are INACTIVE until Claude Code restarts.
  Running Jira skills before restarting will produce
  "tool not found" errors.

  After restarting:
    1. Run /atlassian-pm:doctor    ← verify all systems
    2. Run /atlassian-pm:search-issues  ← test Jira connection
=================================================
```

---

## Examples

### ✅ Good

```text
/setup                                # first-time setup on a fresh machine — installs all deps
/setup                                # safe to re-run after plugin reinstall (idempotent, skips done steps)
/setup                                # run when doctor reports acli not authenticated or mcp-atlassian missing
```

### ❌ Bad

```text
/setup                                # don't run mid-session while a sprint planning skill is active — MCP restart will kill context
/setup --skip-acli                    # no flags exist — setup runs all phases and skips what's already done automatically
/setup                                # don't run just to fix board_id=0 — doctor → Phase 5b handles that without full re-setup
/setup                                # don't run to update a single team member — edit project-config.json directly
```

**Common mistakes:**

- Not restarting Claude Code after setup completes — MCP servers registered during setup are inactive until restart, causing "tool not found" errors in all Jira skills.
- Providing Jira site URL with `https://` prefix — setup strips it, but double-check the stored config has bare hostname format (`your-company.atlassian.net`).
- Ignoring the API token expiry warning — Atlassian tokens expire in ≤365 days; set a calendar reminder or you'll need to re-run setup phases 4a+4b.
- Re-running full setup to change only one thing (e.g., project key) — edit `project-config.json` directly and re-run `/doctor` to validate.

## Error Handling Reference

> See [references/error-handling.md](references/error-handling.md) for per-phase error handling reference.

## 🎓 Domain Expert Notes

### Why This Approach

Setup is engineered as an **idempotent provisioning script** — a concept from infrastructure-as-code where running an operation N times produces the same result as running it once. This matters because developer environments are re-provisioned constantly (plugin reinstalls, machine migrations, onboarding). The Phase 0 detection scan + fast-path skip pattern eliminates the most common onboarding fear: "will re-running this break what I already have?"

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| 12-Factor App — Factor III (Config) | Phase 4a: credentials in `~/.config/atlassian/.env`, not code | Config that varies per-deploy belongs in environment, never in source |
| 12-Factor App — Factor X (Dev/Prod Parity) | Phase 1: pinned tool versions (`mcp-atlassian==0.21.0`, Python 3.11+) | Same dependency versions across all developer machines eliminates "works on my machine" |
| Idempotent provisioning (Terraform/Ansible pattern) | Phase 0 detection + per-flag skip guards | Each phase checks current state before acting — re-runs converge, never diverge |
| Least-privilege secret handling (OWASP) | Phase 4a: `chmod 600` on `.env`, `chmod 700` on directory; token passed via `--env-file` not argv | Secrets visible in `ps aux` output if passed as argv; file-based injection keeps them out of process list |
| Backup-restore resilience | Phase 0/3: auto-restore config from `~/.config/atlassian/` on reinstall | Plugin reinstalls wipe the cache dir; a backup that survives outside the plugin directory is standard IaC recovery pattern |

### Key Metrics

- **Time-to-first-green-doctor:** Target ≤5 minutes on a machine with Homebrew installed. If longer, `brew install acli` or `uv sync` is the bottleneck — check network/proxy.
- **Phases skipped on re-run:** All 5 flags true → 0 interactive phases, straight to Phase 5b validation. A good idempotent setup converges to "nothing to do" on the second run.
- **Token rotation frequency:** Atlassian API tokens expire in ≤365 days. Teams without a calendar reminder will hit auth failures silently — setup warns, but enforcement is human.

### Expert Decision Criteria

**Idempotency guards — when each phase runs:**

- Phase 1 (deps): always checks, installs only if missing — `command -v` before `brew install`
- Phase 2 (config): skipped entirely when `SKIP_CONFIG=true` — existing non-placeholder config is authoritative
- Phase 3 (write): overwrite guard prompts before replacing existing valid config — default is `N` (preserve)
- Phase 4a (env): skipped when `.env` already has non-empty `JIRA_API_TOKEN` — no re-prompting for credentials
- Phase 4b (acli auth): skipped when `acli jira auth status` exits 0 — exit code is more stable than string parsing
- Phase 4c (MCP): skipped when `claude mcp get mcp-atlassian` exits 0 — prevents duplicate registrations

**Configuration drift signals to watch for:**

- `ENV_OK=true` but `ACLI_OK=false` → token in `.env` is stale or expired; re-run phases 4a+4b
- `MCP_OK=true` but tools return "not found" → MCP registered in a previous session, not yet activated — restart Claude Code
- `VENV_OK=false` after plugin reinstall → expected; Phase 1 always re-syncs; data dir naming changed (`atlassian-pm-atlassian-pm`)

**Security decisions:**

- Token collected via chat, written with Write tool (not heredoc/echo) — avoids token appearing in bash history
- Credentials dir `chmod 700`, files `chmod 600` — OWASP Secrets Management minimum for local dev
- Token passed to `mcp-atlassian` via `--env-file` (file path in argv), never the token value itself — keeps secret out of `ps aux` process list

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| "Tool not found" immediately after setup | MCP registered but Claude Code not restarted | Restart Claude Code — MCP servers activate only on session start |
| Phase 4b fails with valid credentials | `acli` reading stale token from OS keychain, not `.env` | Run `acli jira auth logout` then retry Phase 4b manually |
| `uv sync` fails with "no project found" | `PLUGIN_ROOT` resolved to wrong path (multiple plugin versions in cache) | Check `ls ~/.claude/plugins/cache/atlassian-pm/atlassian-pm/` — delete stale versions |
| Config restored from backup but has wrong project key | Backup from a previous project setup was restored | Delete `~/.config/atlassian/atlassian-pm-config.json`, re-run setup with correct values |
| board_id stays 0 after setup | User skipped Phase 5b board lookup | Run `/doctor` — it offers board lookup when `board_id=0` is detected |
| mcp-atlassian registered with wrong project filter | `PROJECT_KEY` collected incorrectly in Phase 2 | Remove with `claude mcp remove mcp-atlassian`, fix config, re-run Phase 4c |

### Authoritative References

- **12factor.net — Factor III (Config):** "Store config in the environment. Config varies across deploys, code does not." The `.env` file pattern is the standard local-dev approximation of environment-injected config.
- **OWASP Secrets Management Cheat Sheet:** Secrets must never appear in process argument lists, logs, or version control. File-based injection (`--env-file`) and `chmod 600` are the minimum viable controls for local development secrets.
- **Infisical — Local Development Secrets Guide:** The core onboarding problem with `.env` files is drift when one developer rotates a secret — setup's backup-restore pattern mitigates this for single-developer plugin reinstalls but does not solve team-wide drift (use a secrets manager for that).
