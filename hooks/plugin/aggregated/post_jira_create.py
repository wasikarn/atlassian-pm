#!/usr/bin/env python3
"""Aggregated: Jira Create PostToolUse — 3 sync hooks in 1 subprocess.

Replaces separate subprocess calls to:
  - guards/post_hr5_parent_verify_remind.py
  - session/post_vs_integrity_track.py
  - guards/post_hr9_alignment_suggest.py

Async hooks (post_skill_checkpoint_track.py, ac_coverage.py) run separately.

Saves ~56ms (2 avoided subprocess startups × 28ms).
"""
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from aggregator import run

HOOKS = [
    PLUGIN_ROOT / "hooks/plugin/guards/post_hr5_parent_verify_remind.py",
    PLUGIN_ROOT / "hooks/plugin/session/post_vs_integrity_track.py",
    PLUGIN_ROOT / "hooks/plugin/guards/post_hr9_alignment_suggest.py",
]

if __name__ == "__main__":
    run(HOOKS, event_name="PostToolUse")
