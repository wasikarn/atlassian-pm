#!/usr/bin/env python3
"""Aggregated: Stop hooks — 2 hooks in 1 subprocess.

Replaces separate subprocess calls to:
  - guards/stop_hr6_unflushed_check.py
  - session/stop_hr5_pending_check.py

Saves ~28ms (1 avoided subprocess startup × 28ms).
"""
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from aggregator import run

HOOKS = [
    PLUGIN_ROOT / "hooks/plugin/guards/stop_hr6_unflushed_check.py",
    PLUGIN_ROOT / "hooks/plugin/session/stop_hr5_pending_check.py",
]

if __name__ == "__main__":
    run(HOOKS, event_name="Stop")
