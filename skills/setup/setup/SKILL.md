---
name: setup
description: |
  First-time setup for atlassian-pm plugin — installs dependencies, collects Jira config,
  creates ~/.config/atlassian/.env, authenticates acli, registers mcp-atlassian, and validates.

  Idempotent: detects what is already configured and skips those steps.
  Re-running is safe — will ask before overwriting existing config.

  Config-file mode: create ~/.atlassian-pm.yaml with --init, fill it in, then run setup for zero-question installation.

  Triggers: "setup", "atlassian-pm setup", "/setup", "install atlassian-pm", "configure plugin"
  Use when: performing initial plugin setup — acli, MCP, credentials, git filters
  Do NOT use for: daily operation (all other skills handle that); upgrading the plugin
x-compatibility: []
argument-hint: "[--init]"
effort: low
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# /atlassian-pm:setup

Guided first-time setup for the `atlassian-pm` plugin. Idempotent — safe to re-run.

## Phase 1 — Config Detection

Run as a **single Bash call** to detect current state. Sets flags used by all later phases.

### `--init` — Create config file template

If the user ran `/atlassian-pm:setup --init`, write the template and exit before any other setup logic.

Insert this at the **very start** of the Phase 1 bash block (before the macOS guard):

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 1: `--init` Detection Script**

**When `--init` is detected:**

1. If `~/.atlassian-pm.yaml` already exists:
   - Print the existing site + project_key (mask api_token — never show it)
   - Ask via AskUserQuestion: "~/.atlassian-pm.yaml already exists. Overwrite?" Buttons: `[Yes, overwrite]` `[No, keep existing]`
   - If **No**: print `"Keeping existing ~/.atlassian-pm.yaml"` and **exit immediately** — do NOT write the template
2. Write the template below via **Write tool** (not bash echo — avoids content in shell history):

```yaml
# atlassian-pm configuration
# Fill in all required fields, then run: /atlassian-pm:setup
#
# ⚠️  This file contains credentials — keep it private.
#     Created with chmod 600. Do not share or commit to git.

jira:
  site: your-company.atlassian.net      # required: bare hostname, no https://
  project_key: PROJ                     # required: uppercase (e.g. BEP, MYPROJ)
  board_id: 0                           # leave as 0 if unknown — setup will offer to look it up

confluence:
  space_key: PROJ                       # optional: defaults to project_key if omitted

credentials:
  email: you@company.com                # required: your Atlassian account email
  api_token: "your-token-here"          # required: https://id.atlassian.com/manage-profile/security/api-tokens
                                        # Note: tokens expire in ≤365 days — set a calendar reminder

# Optional: Figma integration
# figma_token: "figd_..."               # uncomment + fill to configure Figma MCP
```

1. Immediately set permissions:

```bash
chmod 600 "$HOME/.atlassian-pm.yaml"
```

1. Print next steps and exit (no further setup phases run).

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 1: Config Detection Script**

**Second-run fast path:** If all five flags are true after Phase 1: skip Phases 2–5, jump to Phase 6 step 2. The venv check ensures Phase 2 always runs when venv is missing (e.g. after plugin reinstall).

```bash
if [ "$SKIP_CONFIG" = "true" ] && [ "$ENV_OK" = "true" ] && \
   [ "$ACLI_OK" = "true" ] && [ "$MCP_OK" = "true" ] && [ "$VENV_OK" = "true" ]; then
  echo ""
  echo "System already configured (config ✓  credentials ✓  mcp ✓  venv ✓)"
  echo "Running validation only..."
  # → Jump to Phase 6 step 2 (health check)
fi
```

## Phase 2 — Check + Auto-install

Run as a **single Bash call**. Prints status for every dep — both installed and skipped. Skip if fast path triggered in Phase 1.

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 2: Dependency Install Script**

**Error handling:**

- `acli` or `uv` install fail → hard stop (both required)
- `uv sync` fail → warn + continue (cache server optional)

## Phase 3 — Configuration

**Skip entirely if `SKIP_CONFIG=true`.**

**If `YAML_CONFIG=true`:** Read all values from `~/.atlassian-pm.yaml` — skip all questions in this phase.

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 3: YAML Config Parsing Script**

Do **NOT** set `SKIP_CONFIG=true` here — Phase 3 must still write `project-config.json` from these variables.

When `YAML_CONFIG=false`, all interactive questions below run unchanged.

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
   - Accept: positive integer (known) or `0` (unknown — defer to Phase 6 step 2)
   - Store as: `jira.board_id` (integer)

**Optional** (via AskUserQuestion with buttons):

- Team members → `เพิ่มตอนนี้` / `ข้ามก่อน`
- Service paths → `เพิ่มตอนนี้` / `ข้ามก่อน`

## Phase 4 — Write Config

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

## Phase 5 — Credentials & MCP

Three independent sub-steps. Each guarded by Phase 1 flags.

### 1. Create `~/.config/atlassian/.env`

**Skip if `ENV_OK=true`.**

**If `YAML_CONFIG=true` (and `ENV_OK=false`):** Read credentials from YAML file — skip the email + token questions.

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 5: Credentials from YAML Script**

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

After writing `.env` successfully (when `YAML_CONFIG=true` and credentials were read from the config file), offer cleanup via AskUserQuestion:

```text
  ✓  Credentials written from config file

  ⚠️  Your credentials: section in ~/.atlassian-pm.yaml is no longer needed.
     Remove it now? Credentials are safely stored in ~/.config/atlassian/.env (chmod 600)
```

Buttons: `[Yes, remove credentials]` `[Keep for now]`

If **Yes**: read `~/.atlassian-pm.yaml` via Read tool, remove the `credentials:` block (from `credentials:` line through the blank line after `api_token:`), write back via Write tool.

### 2. Authenticate acli

**Skip if `ACLI_OK=true`.**

**Variable sourcing:** Use `EMAIL`/`API_TOKEN` from step 1 if available. If `ENV_OK=true` (step 1 skipped):

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

### 3. Register mcp-atlassian

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

### 4. Configure Figma MCP (optional)

**Always runs — skip logic handled internally by `FIGMA_OK` flag.**

If `FIGMA_OK=true`, print `"  figma MCP: already configured — skipping ✓"` and skip this step.

**If `YAML_CONFIG=true` and `figma_token` is set in YAML (non-empty, not placeholder):**

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 5: Figma Token from YAML Script**

When `FIGMA_TOKEN_FROM_FILE` is empty or placeholder → existing flow (ask user) runs unchanged.

Otherwise, ask via AskUserQuestion:

```
Would you like to configure Figma MCP for design references in skills?
(optional — skip if your team does not use Figma)
```

Buttons: `[Yes, configure]` `[Skip for now]`

If **Skip for now**: print `"  figma MCP: skipped"` and continue to Phase 6.

If **Yes, configure**:

- Print token visibility warning (same text as Phase 5 §1 — token visible in chat, clear session on shared machine, never echoed back).
- Ask: `"What is your Figma Personal Access Token?"` (Hint: Figma → Settings → Security → Personal Access Tokens). **IMPORTANT:** Never echo token back — reference as `[token collected]`.
- Write token to `~/.config/atlassian/.figma.env` via **Write tool** (not shell echo — avoids token in shell history):

  ```dotenv
  FIGMA_API_KEY=<FIGMA_TOKEN>
  ```

- Set permissions and register:

  ```bash
  chmod 600 "${HOME}/.config/atlassian/.figma.env"

  claude mcp add --scope user figma -- npx -y figma-developer-mcp \
    --env-file "${HOME}/.config/atlassian/.figma.env"
  ```

- Verify registration:

  ```bash
  if claude mcp get figma &>/dev/null; then
    echo "  figma MCP: registered (user scope) ✓"
    FIGMA_NEWLY_ADDED=true
  else
    echo "  !  figma MCP: registration may have failed — check: claude mcp list"
  fi
  ```

## Phase 6 — Finalize + Validate

### 1. Run setup.sh

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 6: Finalize Script** (team-detail copy + setup.sh)

Handles: git smudge/clean filter + global `~/.claude/CLAUDE.md` Atlassian block.

### 2. Health Check

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 6: Health Check Script**

**Board ID lookup (if board_id = 0):**

After the Phase 6 step 2 Bash block completes, read `project-config.json`. If `jira.board_id = 0`:

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

### 3. Summary Output

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

### 4. Restart Notice (conditional on `MCP_NEWLY_ADDED=true` OR `FIGMA_NEWLY_ADDED=true`)

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

## Examples

```text
/setup --init    # create ~/.atlassian-pm.yaml template (fill it in, then run /setup)
/setup           # config-file mode: reads ~/.atlassian-pm.yaml if filled, skips all questions
/setup           # first-time setup on a fresh machine — installs all deps
```

**Key mistakes to avoid:**

- Not restarting Claude Code after setup — MCP servers are inactive until restart, causing "tool not found" errors in all Jira skills.
- Providing Jira site URL with `https://` prefix — setup strips it, but double-check stored config has bare hostname format.
- Leaving placeholder values in `~/.atlassian-pm.yaml` — setup detects them and falls back to interactive mode; ensure all 5 required fields have real values.

## Error Handling Reference

> See [references/error-handling.md](references/error-handling.md) for per-phase error handling reference.

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

No shared reference dependencies — all configuration performed via Bash commands only.
