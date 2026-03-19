# Marketplace Setup Design

## Goal

Enable internal team members (~5-7 people) to install the `atlassian-pm` plugin online via Claude Code's marketplace system, with a guided `/atlassian-pm:setup` skill that handles dependencies, configuration, and activation — no manual file editing or repo cloning required.

## Context

- **Repo:** `github.com/wasikarn/jira-generator` (public)
- **Audience:** Internal Tathep team
- **Current state:** Plugin works locally via `claude --plugin-dir .` but has two hooks with hardcoded user-specific values that break on other machines

## Problems to Solve

| Problem | Location | Impact |
| ------- | -------- | ------ |
| Hardcoded absolute paths | `hooks/hooks_state.py:225-229` | QMD collection lookup fails on other machines |
| Hardcoded project key regex | `hooks/pre_prompt_issue_prefetch.py:29,58-59` | Issue prefetch broken for any project key ≠ BEP |
| No marketplace catalog | — | Cannot install via `/plugin marketplace add` |
| No guided setup | — | User must manually edit JSON, install deps, configure git |

---

## Architecture

```text
[1] hooks/config_loader.py        ← NEW: shared util, reads project-config.json
         ↓ imported by
[2] hooks/hooks_state.py          ← FIX: QMD_COLLECTIONS from config
    hooks/pre_prompt_issue_prefetch.py  ← FIX: KEY_RE from config

[3] skills/setup/SKILL.md         ← NEW: /atlassian-pm:setup slash command
         ↓ calls
    scripts/setup.sh              ← UPDATE: add dependency check/install steps

[4] marketplace.json              ← NEW: plugin catalog at repo root
    README.md                     ← UPDATE: add online installation section
```

### Install flow (user perspective)

```text
1. /plugin marketplace add wasikarn/jira-generator
2. /plugin install atlassian-pm@atlassian-pm
3. /atlassian-pm:setup
   ├─ Dependency check + install (acli, uv, jira-cache-server venv)
   ├─ Claude asks: Jira site URL? (chat)
   ├─ Claude asks: Project key? (chat)
   ├─ Claude asks: Board ID? (chat)
   ├─ Claude asks: Add team members now? (AskUserQuestion — optional)
   ├─ Claude asks: Add service paths now? (AskUserQuestion — optional)
   ├─ Claude writes .claude/project-config.json (Write tool)
   └─ Claude runs setup.sh (git filters + sync-skills)
4. ✅ Ready to use
```

---

## Component Designs

### 1. `hooks/config_loader.py` (new file)

Shared utility imported by any hook that needs project config. Uses `lru_cache` to avoid redundant disk reads within a single hook process.

```python
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def load_project_config() -> dict:
    """Load .claude/project-config.json relative to plugin root."""
    config_path = Path(__file__).parent.parent / ".claude" / "project-config.json"
    try:
        return json.loads(config_path.read_text()) if config_path.exists() else {}
    except Exception:
        return {}
```

**Path resolution:** `hooks/config_loader.py` → `../.claude/project-config.json` — works from any working directory because path is relative to `__file__`, not `cwd`. `__file__` is resolved at module load time (fixed path), so the config is always found regardless of the process's current directory. If hooks ever move to a subdirectory, update the `parent.parent` depth accordingly.

**Failure mode:** Returns `{}` on any error (missing file, malformed JSON) — hooks degrade gracefully.

---

### 2. `hooks/hooks_state.py` fix

Replace hardcoded `QMD_COLLECTIONS` dict with config-derived version:

```python
from config_loader import load_project_config

def _build_qmd_collections() -> dict[str, str]:
    config = load_project_config()
    return {
        str(Path(svc["path"]).expanduser()): svc["name"]
        for svc in config.get("services", {}).get("tags", [])
        if svc.get("path") and svc.get("name")
    }

QMD_COLLECTIONS = _build_qmd_collections()
```

`expanduser()` converts `~/Codes/...` → absolute path. Empty dict returned gracefully if config missing.

---

### 3. `hooks/pre_prompt_issue_prefetch.py` fix

Replace hardcoded `BEP-` regex with config-derived project key:

```python
from config_loader import load_project_config

_cfg        = load_project_config()
PROJECT_KEY = _cfg.get("jira", {}).get("project_key", "")
KEY_RE      = re.compile(rf"\b{re.escape(PROJECT_KEY)}-(\d+)\b", re.I) if PROJECT_KEY else None
```

If `PROJECT_KEY` is empty (fresh install before setup) → `KEY_RE = None` → hook exits immediately without error.

Update `main()` to guard against `None`:

```python
if KEY_RE is None or not KEY_RE.findall(prompt):
    sys.exit(0)
```

Also replace the hardcoded normalisation on lines 57-59 where issue keys are reconstructed:

```python
# Before (hardcoded):
k = f"BEP-{n.lstrip('0') or '0'}"  # line 58 — dead code (immediately overwritten)
k = f"BEP-{int(n)}"                 # line 59

# After (config-derived); remove line 58 (dead code), update line 59:
k = f"{PROJECT_KEY}-{int(n)}"
```

Remove line 58 entirely — its value is immediately overwritten by line 59, making it dead code. Keeping it would leave a stale hardcoded `BEP-` in the file.

---

### 4. `skills/setup/SKILL.md` (new skill)

Slash command `/atlassian-pm:setup` — Claude orchestrates the full setup flow.

#### Phase 1 — Dependency Check (Bash tool)

```bash
# Check and install acli
command -v acli || brew install atlassian-cli && \
# Check and install uv; export PATH so uv is available in the same Bash invocation
{ command -v uv || { curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH"; }; } && \
# Install jira-cache-server venv
uv sync --project "$CLAUDE_PLUGIN_ROOT/mcp-servers/jira-cache-server" --extra embeddings
```

> **Important:** All three commands above must run as a **single Bash tool call** (chained with `&&`). The `export PATH` from a previous Bash tool call does not persist into subsequent calls — if `uv` is freshly installed but the commands are split, `uv sync` will fail with "command not found". As a fallback, Phase 1 can use `~/.local/bin/uv sync ...` explicitly.
>
> **Note:** Phase 1 runs dependency checks inline so Claude can report any failures to the user immediately. Phase 4 (`setup.sh`) also contains the same dependency checks — running them twice is harmless because all checks are idempotent (`command -v` / `brew install` skips if already installed).

#### Phase 2 — Configuration (Claude chat + AskUserQuestion)

Required fields (regular chat messages, free-form answers):

1. Jira site URL (e.g. `your-company.atlassian.net`)
2. Project key (e.g. `BEP`) — validate: uppercase alphanumeric only
3. Board ID (hint: run `jira_get_agile_boards(project_key=...)` if unsure)

Optional fields (AskUserQuestion with buttons):

1. Add team members now? → `เพิ่มตอนนี้` / `ข้ามก่อน`
   - If yes: ask name, email, role per member (loop until blank name)
2. Add service paths now? → `เพิ่มตอนนี้` / `ข้ามก่อน`
   - If yes: ask path per service (BE, Admin, Website, etc.)

#### Phase 3 — Write Config (Write tool)

Claude writes `.claude/project-config.json` by:

1. Reading `config/project-config.json.template` (authoritative template — `setup.sh` also reads from `config/`, not `.claude/`)
2. Substituting answered values
3. Writing to `.claude/project-config.json`

#### Phase 4 — Finalize (Bash tool)

```bash
cd "$CLAUDE_PLUGIN_ROOT" && ./scripts/setup.sh
```

`setup.sh` handles git filter + sync-skills (dependency steps already done in Phase 1).

#### Summary output

```text
✅ atlassian-pm setup complete
Jira: [site] / Project: [key] / Board: [id]
→ /atlassian-pm:story-full to create your first story
```

---

### 5. `scripts/setup.sh` update

Add dependency checks at the top (before existing steps):

```bash
# --- 0a. Check + install dependencies ---
echo "[0/4] Checking dependencies..."

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

echo "  Installing jira-cache-server venv..."
uv sync --project "$PROJECT_DIR/mcp-servers/jira-cache-server" --extra embeddings --quiet
```

Existing steps 0-4 remain unchanged. `setup.sh` is still usable standalone for dev/re-configuration.

---

### 6. `marketplace.json` (new file at repo root)

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

---

### 7. `README.md` update

Add "Online Installation" section before the existing "Installation" section:

```markdown
## Online Installation (Recommended)

### Step 1 — Add marketplace
/plugin marketplace add wasikarn/jira-generator

### Step 2 — Install plugin
/plugin install atlassian-pm@atlassian-pm

### Step 3 — Run setup
/atlassian-pm:setup
```

Existing manual installation steps remain for dev/local use.

---

## Files Changed

| Action | File |
| ------ | ---- |
| Create | `hooks/config_loader.py` |
| Modify | `hooks/hooks_state.py` |
| Modify | `hooks/pre_prompt_issue_prefetch.py` |
| Create | `skills/setup/SKILL.md` |
| Modify | `scripts/setup.sh` |
| Create | `marketplace.json` |
| Modify | `README.md` |

## Files NOT Changed

- `config/project-config.json.template` — already uses generic placeholder values
- `.gitignore` — already excludes `.claude/project-config.json`
- `.gitattributes` — no longer needs `hooks/*.py` since hooks now read config at runtime
- All other hooks — not affected (only 2 hooks had hardcoded values)

## Out of Scope

- Publishing to Anthropic's official marketplace
- npm package distribution
- Confluence/Jira credential management (handled separately via `acli login` + MCP env vars)
- Multi-project support (single `project-config.json` per install)
