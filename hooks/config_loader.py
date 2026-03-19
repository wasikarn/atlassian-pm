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
