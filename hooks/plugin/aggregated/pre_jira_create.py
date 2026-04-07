#!/usr/bin/env python3
"""Aggregated: Jira Create PreToolUse — 2 hooks in 1 subprocess.

Replaces separate subprocess calls to:
  - cache/pre_search_before_create.py
  - guards/pre_hr5_parent_verify_block.py

Saves ~28ms (1 avoided subprocess startup × 28ms).
"""
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from aggregator import run

HOOKS = [
    PLUGIN_ROOT / "hooks/plugin/cache/pre_search_before_create.py",
    PLUGIN_ROOT / "hooks/plugin/guards/pre_hr5_parent_verify_block.py",
]

if __name__ == "__main__":
    run(HOOKS, event_name="PreToolUse")
