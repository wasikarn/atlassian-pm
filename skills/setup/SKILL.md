---
name: setup
description: |
  First-time setup for atlassian-pm plugin — installs dependencies, collects Jira config,
  writes .claude/project-config.json, and runs git filter setup.

  Triggers: "setup", "atlassian-pm setup", "/setup", "install atlassian-pm", "configure plugin"
argument-hint: ""
---

# /atlassian-pm:setup

Guided first-time setup for the `atlassian-pm` plugin.

## Overview

| Phase | What happens |
| ----- | ------------ |
| 1. Dependencies | Check + install `acli`, `uv`, jira-cache-server venv |
| 2. Configuration | Ask Jira URL, project key, board ID (+ optional team + services) |
| 3. Write Config | Write `.claude/project-config.json` from template |
| 4. Finalize | Run `scripts/setup.sh` (git filters + sync-skills) |

---

## Phase 1 — Dependency Check

Run as a **single Bash tool call**:

```bash
# 1a. acli
command -v acli || brew install atlassian-cli

# 1b. uv (use explicit path so venv install works even if just installed)
command -v uv || curl -LsSf https://astral.sh/uv/install.sh | sh
UV_BIN="${HOME}/.local/bin/uv"
command -v uv &>/dev/null && UV_BIN="uv"

# 1c. jira-cache-server venv
"$UV_BIN" sync --project "$CLAUDE_PLUGIN_ROOT/mcp-servers/jira-cache-server" --extra embeddings
```

If any step fails → report error to user and stop. Do not proceed to Phase 2.

---

## Phase 2 — Configuration

Ask questions in order. Each is a plain chat message (free-form text answer). Validate where noted.

**Required fields:**

1. **Jira site URL**
   - Ask: "What is your Jira site URL? (e.g. `your-company.atlassian.net`)"
   - Strip `https://` prefix if user includes it
   - Store as: `jira.site` and `confluence.site`

2. **Project key**
   - Ask: "What is your Jira project key? (e.g. `BEP`, `PROJ`)"
   - Validate: uppercase letters + digits only (`^[A-Z][A-Z0-9]+$`) — re-ask if invalid
   - Store as: `jira.project_key`

3. **Board ID**
   - Ask: "What is your Jira board ID? (hint: I can look it up — just say 'look it up' and I'll call `jira_get_agile_boards`)"
   - If user says "look it up" → call `MCP: jira_get_agile_boards(project_key="<key>")` and show results
   - Store as: `jira.board_id` (integer)

**Optional fields — use AskUserQuestion with buttons:**

1. **Team members**
   - Ask via AskUserQuestion: "เพิ่มสมาชิกทีมตอนนี้?" → buttons: `เพิ่มตอนนี้` / `ข้ามก่อน`
   - If เพิ่มตอนนี้: ask for each member in a loop (name, email, role) until user enters blank name
   - Store as: `team.members[]`

2. **Service paths**
   - Ask via AskUserQuestion: "เพิ่ม service paths ตอนนี้?" → buttons: `เพิ่มตอนนี้` / `ข้ามก่อน`
   - If เพิ่มตอนนี้: ask for each service (tag, name, path) until user enters blank
   - Paths may use `~` prefix (e.g. `~/Projects/api`)
   - Store as: `services.tags[]`

---

## Phase 3 — Write Config

1. Read `$CLAUDE_PLUGIN_ROOT/config/project-config.json.template` using Read tool
2. Build the config object by substituting collected values into the template structure:
   - Replace template placeholder values (e.g. `acme-corp.atlassian.net` → real site)
   - Keep all template structure, comments, and non-answered fields as-is
   - Set `jira.board_id` as integer (not string)
   - If team was skipped → keep template placeholder members
   - If services were skipped → write `"tags": []` (empty array, not template placeholders)
3. Write to `$CLAUDE_PLUGIN_ROOT/.claude/project-config.json` using Write tool

---

## Phase 4 — Finalize

```bash
cd "$CLAUDE_PLUGIN_ROOT" && ./scripts/setup.sh
```

`setup.sh` handles: git smudge/clean filter configuration, sync-skills to `~/.claude/skills/`, and global `CLAUDE.md` Atlassian settings block. Dependency steps will re-run but are idempotent (safe).

---

## Summary Output

After Phase 4 completes successfully:

```text
✅ atlassian-pm setup complete

Jira:    [site] / Project: [key] / Board: [board_id]
Config:  [CLAUDE_PLUGIN_ROOT]/.claude/project-config.json

→ /atlassian-pm:story-full to create your first story
→ /atlassian-pm:plan-sprint for sprint planning
```

---

## Error Handling

| Phase | Error | Action |
| ----- | ----- | ------ |
| 1 | `brew` not found | Tell user to install Homebrew first: `https://brew.sh` |
| 1 | `uv sync` fails | Show error, suggest: `cd mcp-servers/jira-cache-server && uv sync --extra embeddings` |
| 2 | Invalid project key | Re-ask with format reminder |
| 3 | Write permission denied | Tell user to check directory permissions |
| 4 | `setup.sh` fails | Show error output, suggest running manually: `./scripts/setup.sh` |
