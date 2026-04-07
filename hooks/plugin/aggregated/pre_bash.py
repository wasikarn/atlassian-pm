#!/usr/bin/env python3
"""Aggregated: Bash PreToolUse — 3 hooks in 1 subprocess.

Replaces separate subprocess calls to:
  - quality/pre_adf_structure_validate.py
  - quality/pre_event_ac_check.py
  - guards/pre_hr1_quality_gate.py

Saves ~56ms (2 avoided subprocess startups × 28ms).
"""
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from aggregator import run

HOOKS = [
    PLUGIN_ROOT / "hooks/plugin/quality/pre_adf_structure_validate.py",
    PLUGIN_ROOT / "hooks/plugin/quality/pre_event_ac_check.py",
    PLUGIN_ROOT / "hooks/plugin/guards/pre_hr1_quality_gate.py",
]

if __name__ == "__main__":
    run(HOOKS, event_name="PreToolUse")
