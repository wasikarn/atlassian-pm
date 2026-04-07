#!/usr/bin/env python3
"""Aggregated: Jira Get PostToolUse — 2 sync hooks in 1 subprocess.

Replaces separate subprocess calls to:
  - guards/post_hr5_parent_verify_clear.py
  - session/post_vs_integrity_track.py

Async hook (post_event_model_track.py) runs separately.

Saves ~28ms (1 avoided subprocess startup × 28ms).
"""
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from aggregator import run

HOOKS = [
    PLUGIN_ROOT / "hooks/plugin/guards/post_hr5_parent_verify_clear.py",
    PLUGIN_ROOT / "hooks/plugin/session/post_vs_integrity_track.py",
]

if __name__ == "__main__":
    run(HOOKS, event_name="PostToolUse")
