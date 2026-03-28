#!/usr/bin/env python3
"""claude -p wrapper for monitor — same guard as scripts/ai/claude_runner.py."""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_TIMEOUT = 20
_MAX_BUDGET_USD = 0.01  # monitor daemon — cap per call like hooks


def run_claude(
    prompt: str,
    timeout: int = _TIMEOUT,
    system_prompt: str | None = None,
) -> str | None:
    """Call `claude -p` and return plain text response, or None on any error.

    Args:
        prompt:        The prompt to send to claude.
        timeout:       Subprocess timeout in seconds (default 20).
        system_prompt: Optional system prompt passed via --system-prompt.
    """
    if os.environ.get(RECURSION_GUARD):
        return None
    env = {**os.environ, RECURSION_GUARD: "1"}
    try:
        proc = subprocess.run(
            [
                "claude", "-p", prompt,
                "--output-format", "json",
                *(["--system-prompt", system_prompt] if system_prompt else []),
            ],
            env=env, capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if data.get("is_error"):
        return None
    return data.get("result") or None


def run_claude_json(
    prompt: str,
    json_schema: dict,
    timeout: int = _TIMEOUT,
    system_prompt: str | None = None,
) -> dict | None:
    """Call `claude -p --json-schema` and return validated structured dict.

    Uses Claude's native schema enforcement — output lands in `structured_output`.
    Eliminates manual JSON parsing and fence stripping.

    Args:
        prompt:        The prompt to send to claude.
        json_schema:   JSON Schema dict — Claude's output is validated against this.
        timeout:       Subprocess timeout in seconds (default 20).
        system_prompt: Optional system prompt passed via --system-prompt.
    """
    if os.environ.get(RECURSION_GUARD):
        return None
    env = {**os.environ, RECURSION_GUARD: "1"}
    try:
        proc = subprocess.run(
            [
                "claude", "-p", prompt,
                "--output-format", "json",
                "--json-schema", json.dumps(json_schema),
                *(["--system-prompt", system_prompt] if system_prompt else []),
            ],
            env=env, capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if data.get("is_error"):
        return None
    structured = data.get("structured_output")
    return structured if isinstance(structured, dict) else None
