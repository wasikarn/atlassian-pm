#!/usr/bin/env python3
"""Thin wrapper around `claude -p` for scripts/ai/ scripts.

Same recursion guard and auth design as hooks/plugin/ai/claude_call.py.
NOT using --bare: plugin runs inside Claude Code session (OAuth auth).
--bare requires ANTHROPIC_API_KEY and disables OAuth.
"""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_TIMEOUT = 20
_MAX_BUDGET_USD = 0.05  # scripts run on-demand; sonnet calls may cost more than hooks


def run_claude(
    prompt: str,
    timeout: int = _TIMEOUT,
    model: str = "haiku",
) -> str | None:
    """Call `claude -p` and return plain text response, or None on any error.

    Args:
        prompt:  The prompt to send to claude.
        timeout: Subprocess timeout in seconds (default 20).
        model:   Claude model alias — "haiku" (default), "sonnet", or "opus".
    """
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
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
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


def run_claude_json(
    prompt: str,
    json_schema: dict,
    timeout: int = _TIMEOUT,
    model: str = "haiku",
) -> dict | None:
    """Call `claude -p --json-schema` and return validated structured dict.

    Uses Claude's native schema enforcement — output lands in `structured_output`.
    Eliminates manual JSON parsing and fence stripping.

    Args:
        prompt:      The prompt to send to claude.
        json_schema: JSON Schema dict — Claude's output is validated against this.
        timeout:     Subprocess timeout in seconds (default 20).
        model:       Claude model alias — "haiku" (default), "sonnet", or "opus".
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
                "--model", model,
                "--max-turns", "1",
                "--max-budget-usd", str(_MAX_BUDGET_USD),
                "--tools", "",
                "--dangerously-skip-permissions",
                "--no-session-persistence",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
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
