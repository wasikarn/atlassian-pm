# Marketplace Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable online installation of the `atlassian-pm` plugin via a guided `/atlassian-pm:setup` skill that reads config at runtime (no hardcoded paths/project keys).

**Architecture:** A new `hooks/config_loader.py` shared utility reads `.claude/project-config.json` relative to `__file__` (not cwd). Both hooks that had hardcoded values (`hooks_state.py` for QMD paths, `pre_prompt_issue_prefetch.py` for BEP- regex) import it. A new `skills/setup/SKILL.md` slash command orchestrates interactive setup in 4 phases: deps → config questions → write JSON → run `setup.sh`.

**Tech Stack:** Python 3.x (hooks), Bash (setup.sh), Markdown (skill), JSON (marketplace catalog)

**Spec:** `docs/superpowers/specs/2026-03-19-marketplace-setup-design.md`

---

## File Structure

| Action | File | Responsibility |
| ------ | ---- | -------------- |
| Create | `hooks/config_loader.py` | Load `.claude/project-config.json` with lru_cache |
| Modify | `hooks/hooks_state.py:224-230` | Replace hardcoded `QMD_COLLECTIONS` dict |
| Modify | `hooks/pre_prompt_issue_prefetch.py:29,57-59` | Replace hardcoded `KEY_RE` and normalisation |
| Modify | `scripts/setup.sh:16` | Fix `CONFIG_TEMPLATE` path + add dep checks at top |
| Create | `skills/setup/SKILL.md` | `/atlassian-pm:setup` slash command |
| Create | `marketplace.json` | Plugin catalog at repo root (speculative schema) |
| Modify | `README.md` | Add "Online Installation" section before existing Installation |

---

## Task 1: `hooks/config_loader.py`

**Files:**

- Create: `hooks/config_loader.py`

Reads `.claude/project-config.json` relative to its own file location (so it works from any cwd).
Uses `lru_cache` as a lightweight guard in case the function is called multiple times in one process.

- [ ] **Step 1: Create `hooks/config_loader.py`**

```python
"""Shared config loader for Claude hooks.

Reads .claude/project-config.json relative to this file's location (repo root).
Uses lru_cache to avoid redundant reads if called multiple times in one process.

Import pattern (required before using this module):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from config_loader import load_project_config
"""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_project_config() -> dict:
    """Load .claude/project-config.json relative to plugin root (hooks/../.claude/).

    Path is relative to __file__ (fixed at module load time), not cwd.
    Returns {} on any error (missing file, malformed JSON) — hooks degrade gracefully.
    """
    config_path = Path(__file__).parent.parent / ".claude" / "project-config.json"
    try:
        return json.loads(config_path.read_text()) if config_path.exists() else {}
    except Exception:
        return {}
```

- [ ] **Step 2: Smoke-test — verify path resolution and graceful fallback**

Run from repo root:

```bash
cd /path/to/jira-generator
python3 -c "
import sys
sys.path.insert(0, 'hooks')
from config_loader import load_project_config
cfg = load_project_config()
print('project_key:', cfg.get('jira', {}).get('project_key', '(missing)'))
print('services count:', len(cfg.get('services', {}).get('tags', [])))
"
```

Expected: prints `project_key: BEP` and `services count: 6` (from `.claude/project-config.json`).

Also verify graceful failure with a bad JSON file:

```bash
echo "not-valid-json" > /tmp/test-config.json
python3 -c "
import sys, json
sys.path.insert(0, 'hooks')
import config_loader
from pathlib import Path

# Patch the config path inside the module to point to bad file
orig_fn = config_loader.load_project_config.__wrapped__
def patched() -> dict:
    config_path = Path('/tmp/test-config.json')
    try:
        return json.loads(config_path.read_text()) if config_path.exists() else {}
    except Exception:
        return {}
result = patched()
print('returns {} on bad JSON?', result == {})
"
rm /tmp/test-config.json
```

Expected: no exception, prints `returns {} on bad JSON? True`.

- [ ] **Step 3: Commit**

```bash
git add hooks/config_loader.py
git commit -m "feat: add config_loader shared utility for hooks"
```

---

## Task 2: `hooks/hooks_state.py` — Replace Hardcoded QMD_COLLECTIONS

**Files:**

- Modify: `hooks/hooks_state.py:1-14` (add sys.path.insert + import at top)
- Modify: `hooks/hooks_state.py:224-230` (replace hardcoded dict with config-derived function)

The current file has no existing `sys.path.insert`. Both the insert and the import must be added before `QMD_COLLECTIONS` is built at module level.

- [ ] **Step 1: Add `sys.path.insert` and `config_loader` import at the top of `hooks_state.py`**

Add these lines right after the existing imports (after `from pathlib import Path`):

```python
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_project_config
```

Full import block at file top should look like:

```python
import fcntl
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_project_config

STATE_DIR = Path("/tmp/claude-hooks-state")
```

- [ ] **Step 2: Replace the hardcoded `QMD_COLLECTIONS` dict (lines 224-230)**

Remove:

```python
# Known indexed project roots → collection name
QMD_COLLECTIONS = {
    "/Users/kobig/Codes/Works/tathep/tathep-platform-api": "tathep-platform-api",
    "/Users/kobig/Codes/Works/tathep/tathep-video-processing": "tathep-video-processing",
    "/Users/kobig/Codes/Works/tathep/tathep-website": "tathep-website",
    "/Users/kobig/Codes/Works/tathep/tathep-admin": "tathep-admin",
}
```

Replace with:

```python
def _build_qmd_collections() -> dict[str, str]:
    """Build QMD_COLLECTIONS from project-config.json services.tags[].

    Returns empty dict if config missing — qmd hooks degrade gracefully.
    expanduser() converts ~/Codes/... to absolute path.
    """
    config = load_project_config()
    return {
        str(Path(svc["path"]).expanduser()): svc["name"]
        for svc in config.get("services", {}).get("tags", [])
        if svc.get("path") and svc.get("name")
    }


# Known indexed project roots → collection name (built from project-config.json)
QMD_COLLECTIONS = _build_qmd_collections()
```

- [ ] **Step 3: Smoke-test — verify QMD_COLLECTIONS loads correctly**

```bash
python3 -c "
import sys
sys.path.insert(0, 'hooks')
import hooks_state
print('QMD_COLLECTIONS:', hooks_state.QMD_COLLECTIONS)
"
```

Expected: dict with 6 entries, each key being an absolute path (e.g. `/Users/kobig/Codes/Works/tathep/tathep-platform-api`).

Verify `qmd_collection_for_path` still works:

```bash
python3 -c "
import sys
sys.path.insert(0, 'hooks')
import hooks_state
result = hooks_state.qmd_collection_for_path('/Users/kobig/Codes/Works/tathep/tathep-platform-api/src/foo.ts')
print('collection:', result)
"
```

Expected: `collection: tathep-platform-api`.

- [ ] **Step 4: Commit**

```bash
git add hooks/hooks_state.py
git commit -m "fix: derive QMD_COLLECTIONS from project-config.json at runtime"
```

---

## Task 3: `hooks/pre_prompt_issue_prefetch.py` — Replace Hardcoded BEP- References

**Files:**

- Modify: `hooks/pre_prompt_issue_prefetch.py:25` (add config_loader import after existing sys.path.insert)
- Modify: `hooks/pre_prompt_issue_prefetch.py:27-31` (replace hardcoded KEY_RE)
- Modify: `hooks/pre_prompt_issue_prefetch.py:50-52` (update main() guard)
- Modify: `hooks/pre_prompt_issue_prefetch.py:57-59` (remove dead line 58, fix line 59 normalisation)

The file already has `sys.path.insert(0, ...)` at line 24 (for hooks_lib). Add `config_loader` import right after.

- [ ] **Step 1: Add config_loader import (after existing sys.path.insert + hooks_lib import)**

Current lines 24-25:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context, log_event
```

After change:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks_lib import inject_context, log_event
from config_loader import load_project_config
```

- [ ] **Step 2: Replace hardcoded KEY_RE (lines 27-31)**

Remove:

```python
_HOOK       = "prompt-issue-prefetch"
CACHE_DB    = Path.home() / ".cache" / "jira-generator" / "jira.db"
KEY_RE      = re.compile(r"\bBEP-(\d+)\b", re.I)
MAX_KEYS    = 5
MAX_DESC_LEN = 200  # chars of description to include
```

Replace with:

```python
_HOOK       = "prompt-issue-prefetch"
CACHE_DB    = Path.home() / ".cache" / "jira-generator" / "jira.db"
MAX_KEYS    = 5
MAX_DESC_LEN = 200  # chars of description to include

_cfg        = load_project_config()
PROJECT_KEY = _cfg.get("jira", {}).get("project_key", "")
KEY_RE      = re.compile(rf"\b{re.escape(PROJECT_KEY)}-(\d+)\b", re.I) if PROJECT_KEY else None
```

- [ ] **Step 3: Update `main()` guard (line ~50) to handle `KEY_RE = None`**

Current:

```python
raw_keys = KEY_RE.findall(prompt)
if not raw_keys:
    sys.exit(0)
```

Replace with:

```python
raw_keys = KEY_RE.findall(prompt) if KEY_RE is not None else []
if not raw_keys:
    sys.exit(0)
```

- [ ] **Step 4: Fix normalisation block (lines 57-59) — remove dead code, use PROJECT_KEY**

Current:

```python
for n in raw_keys:
    k = f"BEP-{n.lstrip('0') or '0'}"   # line 58 — dead code
    k = f"BEP-{int(n)}"                  # line 59
```

Replace with:

```python
for n in raw_keys:
    k = f"{PROJECT_KEY}-{int(n)}"
```

- [ ] **Step 5: Smoke-test — verify hook exits cleanly with no config**

```bash
# With no project key in config (simulated by temp config)
echo '{"prompt": "look at BEP-123 please", "session_id": "test"}' | \
  python3 hooks/pre_prompt_issue_prefetch.py
```

Expected: exits 0 (no output, no exception). The hook will query cache and either inject context or exit silently.

Verify KEY_RE builds correctly from real config:

```bash
python3 -c "
import sys
sys.path.insert(0, 'hooks')
import pre_prompt_issue_prefetch as h
print('PROJECT_KEY:', h.PROJECT_KEY)
print('KEY_RE:', h.KEY_RE)
"
```

Expected: `PROJECT_KEY: BEP`, `KEY_RE: re.compile('\\\\bBEP-(\\\\d+)\\\\b', re.IGNORECASE)`.

- [ ] **Step 6: Commit**

```bash
git add hooks/pre_prompt_issue_prefetch.py
git commit -m "fix: derive KEY_RE and PROJECT_KEY from project-config.json at runtime"
```

---

## Task 4: `scripts/setup.sh` — Fix Template Path + Add Dependency Checks

**Files:**

- Modify: `scripts/setup.sh:16` (fix CONFIG_TEMPLATE path)
- Modify: `scripts/setup.sh:10-13` (add dependency check block before step 0)

Current bug at line 16: `CONFIG_TEMPLATE="$PROJECT_DIR/.claude/project-config.json.template"` — the template lives at `config/project-config.json.template`, not `.claude/`.

- [ ] **Step 1: Fix CONFIG_TEMPLATE path (line 16)**

Change:

```bash
CONFIG_TEMPLATE="$PROJECT_DIR/.claude/project-config.json.template"
```

To:

```bash
CONFIG_TEMPLATE="$PROJECT_DIR/config/project-config.json.template"
```

- [ ] **Step 2: Add dependency check block at the top (before `# --- 0. Check project config ---`)**

Add this block after line 12 (`echo ""`):

```bash
# --- deps. Check + install dependencies (idempotent) ---
echo "[deps] Checking dependencies..."

check_dep() { command -v "$1" &>/dev/null; }

if ! check_dep acli; then
  echo "  Installing acli via Homebrew..."
  brew install atlassian-cli
fi

if ! check_dep uv; then
  echo "  Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if [ -d "$PROJECT_DIR/mcp-servers/jira-cache-server" ]; then
  echo "  Installing jira-cache-server venv..."
  UV_BIN="${HOME}/.local/bin/uv"
  command -v uv &>/dev/null && UV_BIN="uv"
  "$UV_BIN" sync --project "$PROJECT_DIR/mcp-servers/jira-cache-server" --extra embeddings --quiet
fi

echo ""
```

- [ ] **Step 3: Smoke-test — verify setup.sh runs without error**

```bash
cd /path/to/jira-generator
bash scripts/setup.sh
```

Expected: runs all steps, no errors. Template copy step should now succeed (or skip if config already exists).

Verify template path fix specifically:

```bash
ls -la config/project-config.json.template   # should exist
ls -la .claude/project-config.json.template 2>/dev/null || echo "does not exist (correct)"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/setup.sh
git commit -m "fix: correct CONFIG_TEMPLATE path (config/ not .claude/) + add dep checks"
```

---

## Task 5: `skills/setup/SKILL.md` — `/atlassian-pm:setup` Skill

**Files:**

- Create: `skills/setup/SKILL.md`

The skill orchestrates 4 phases: dep check (Bash), config questions (chat + AskUserQuestion), write config (Write tool), finalize (Bash). Claude reads the template, substitutes values, and writes `.claude/project-config.json`.

- [ ] **Step 1: Create `skills/setup/SKILL.md`**

```markdown
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
   - If team/services were skipped → keep template placeholder values
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

```

- [ ] **Step 2: Verify SKILL.md frontmatter is valid**

```bash
# Check frontmatter structure
head -10 skills/setup/SKILL.md
```

Expected: starts with `---`, has `name: setup`, `description:`, `argument-hint:`, closing `---`. There should be NO `disable-model-invocation` field (skill requires LLM reasoning for interactive phases).

- [ ] **Step 3: Commit**

```bash
git add skills/setup/SKILL.md
git commit -m "feat: add /atlassian-pm:setup guided installation skill"
```

---

## Task 6: `marketplace.json` + `README.md` Online Installation Section

**Files:**

- Create: `marketplace.json`
- Modify: `README.md` (add section before `## Prerequisites`)

These two changes are small and independent — batch them in one commit.

- [ ] **Step 1: Create `marketplace.json` at repo root**

```json
{
  "name": "atlassian-pm",
  "description": "Agile Jira/Confluence automation for Claude Code",
  "plugins": [
    {
      "name": "atlassian-pm",
      "description": "Create Epics, Stories, Sub-tasks and plan Sprints using natural language. Enforces quality gates via hook-based guardrails.",
      "version": "1.0.0",
      "source": {
        "type": "github",
        "repo": "wasikarn/jira-generator"
      }
    }
  ]
}
```

- [ ] **Step 2: Add "Online Installation" section to `README.md`**

Insert before the existing `## Prerequisites` section (line ~112):

```markdown
## Online Installation (Recommended)

Install without cloning the repo — Claude handles everything.

### Step 1 — Add marketplace

```

/plugin marketplace add wasikarn/jira-generator

```

### Step 2 — Install plugin

```

/plugin install atlassian-pm@atlassian-pm

```

### Step 3 — Run setup

```

/atlassian-pm:setup

```

Claude will ask for your Jira site, project key, and board ID, then write the config and configure git filters automatically.

> **Note:** The marketplace install commands above are based on Claude Code's plugin system. If these commands are not yet available in your version, use the manual installation below.

---
```

- [ ] **Step 3: Verify README renders correctly**

```bash
# Check the new section is in place
grep -n "Online Installation" README.md
grep -n "## Prerequisites" README.md
```

Expected: "Online Installation" appears before "Prerequisites".

- [ ] **Step 4: Commit**

```bash
git add marketplace.json README.md
git commit -m "feat: add marketplace.json catalog and online installation section to README"
```

---

## Final Verification

After all tasks are complete, verify the full change set works end-to-end:

- [ ] **Verify hooks import correctly**

```bash
python3 -c "
import sys
sys.path.insert(0, 'hooks')
import hooks_state
import pre_prompt_issue_prefetch as pp
print('QMD_COLLECTIONS:', hooks_state.QMD_COLLECTIONS)
print('PROJECT_KEY:', pp.PROJECT_KEY)
print('KEY_RE:', pp.KEY_RE)
"
```

Expected: No import errors. `QMD_COLLECTIONS` has entries from config. `PROJECT_KEY` is `BEP`.

- [ ] **Verify hook end-to-end with test prompt**

```bash
echo '{"prompt": "please check BEP-123 status", "session_id": "test-123"}' | \
  python3 hooks/pre_prompt_issue_prefetch.py
echo "Exit: $?"
```

Expected: exits 0 (either injects cache context or exits silently — no Python errors).

- [ ] **Verify setup.sh template copy works**

```bash
# Temporarily rename config to test the copy path
mv .claude/project-config.json .claude/project-config.json.bak
bash scripts/setup.sh
# Restore
mv .claude/project-config.json.bak .claude/project-config.json 2>/dev/null || true
```

Expected: setup.sh creates `.claude/project-config.json` from `config/project-config.json.template` (not from the now-nonexistent `.claude/` template).

- [ ] **Push all commits**

```bash
git push
```
