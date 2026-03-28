#!/usr/bin/env python3
"""claude -p wrapper for monitor — same guard as scripts/ai/claude_runner.py."""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_TIMEOUT = 20


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
                "--allowedTools", "",
                "--dangerously-skip-permissions",
            ],
            env=env, capture_output=True, text=True, timeout=timeout,
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
