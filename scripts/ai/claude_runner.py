#!/usr/bin/env python3
"""Thin wrapper around `claude -p` for scripts/ai/ scripts.

Same recursion guard as hooks/plugin/ai/claude_call.py.
"""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_TIMEOUT = 20


def run_claude(prompt: str, timeout: int = _TIMEOUT) -> str | None:
    """Call `claude -p` and return plain text response, or None on any error."""
    if os.environ.get(RECURSION_GUARD):
        return None

    env = {**os.environ, RECURSION_GUARD: "1"}
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    if proc.returncode != 0 or not proc.stdout.strip():
        return None

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    if data.get("is_error"):
        return None
    return data.get("result") or None
