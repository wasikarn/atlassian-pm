#!/usr/bin/env python3
"""SessionStart: Check required tools and paths are available.

Runs on every session start (no matcher = all sessions).
Advisory only — NEVER blocks. Injects warnings for missing tools.

Checks:
  - acli: required for Jira writes (HR3), subtask two-step (HR5)
  - qmd: required for auto-search hook (pre_qmd_auto_search)
  - cache DB: required for HR10 subtask detection, HR5 cross-session state
  - state dir: required for session state (HR5, HR6, HR7 tracking)
"""

import os
import shutil
import sys
from pathlib import Path

CACHE_DB = Path(os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".cache" / "atlassian-pm"))) / "jira.db"
STATE_DIR = Path("/tmp/claude-hooks-state")

warnings = []

# Check CLI tools
if not shutil.which("acli"):
    warnings.append(
        "⚠️  acli not found on PATH. Required for: Jira writes (HR3), subtask creation (HR5).\n"
        "   Install: https://acli.atlassian.com or check PATH config."
    )

if not shutil.which("qmd"):
    warnings.append(
        "⚠️  qmd not found on PATH. QMD auto-search hook disabled (Glob/Grep will proceed normally).\n"
        "   Optional install: bun install -g qmd or add bun bin to PATH."
    )

# Check cache DB
if not CACHE_DB.exists():
    warnings.append(
        f"⚠️  Jira cache DB not found: {CACHE_DB}\n"
        "   HR10 subtask detection (cross-session) and cache-prefer hook degraded.\n"
        "   Start jira-cache-server MCP to initialize: see jira-cache-server/SKILL.md"
    )

# Check state dir writable
try:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    test_file = STATE_DIR / ".write-test"
    test_file.touch()
    test_file.unlink()
except OSError as e:
    warnings.append(
        f"⚠️  Session state dir not writable: {STATE_DIR} ({e})\n"
        "   HR5/HR6/HR7 session tracking will fail. Check /tmp permissions."
    )

if warnings:
    print("\n".join(warnings))

sys.exit(0)
