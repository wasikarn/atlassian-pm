#!/usr/bin/env python3
"""claude -p wrapper for monitor — same recursion guard as scripts/ai/claude_runner.py.

NOT using --bare: monitor inherits Claude Code session's OAuth credentials.
If running as a standalone daemon with ANTHROPIC_API_KEY, add --bare flag.
"""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_TIMEOUT = 20
_MAX_BUDGET_USD = 0.01  # monitor polls continuously — cap per analysis call


def run_claude(
    prompt: str,
    timeout: int = _TIMEOUT,
    model: str = "haiku",
) -> str | None:
    if os.environ.get(RECURSION_GUARD):
        return None
    env = {**os.environ, RECURSION_GUARD: "1"}
    try:
        proc = subprocess.run(
            [
                "claude", "-p", prompt,
                "--output-format", "json",
                "--model", model,
                "--max-turns", "1",
                "--max-budget-usd", str(_MAX_BUDGET_USD),
                "--tools", "",
                "--dangerously-skip-permissions",
                "--no-session-persistence",
            ],
            env=env, capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    # Per official docs: Claude outputs JSON to stdout even on non-zero exit.
    if not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if data.get("is_error"):
        return None
    return data.get("result") or None
