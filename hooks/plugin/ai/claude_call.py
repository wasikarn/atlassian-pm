#!/usr/bin/env python3
"""Shared utility: call `claude -p` for LLM reasoning in hooks and scripts.

Two entry points:
    claude_call()      — returns raw text (str | None); callers parse with parse_json()
    claude_call_json() — uses --json-schema; returns validated dict | None directly

Recursion guard: sets ATLASSIAN_PM_HOOK_DEPTH=1 in subprocess env.
Any hook that checks this var on entry will skip the AI call,
preventing infinite loops when claude -p fires a new Claude Code session.
"""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_CLAUDE_TIMEOUT = 15  # seconds


def claude_call(
    prompt: str,
    timeout: int = _CLAUDE_TIMEOUT,
    model: str = "haiku",
) -> str | None:
    """Call `claude -p` non-interactively and return the text response.

    Args:
        prompt:  The prompt to send to claude.
        timeout: Subprocess timeout in seconds (default 15).
        model:   Claude model alias — "haiku" (default), "sonnet", or "opus".

    Returns:
        The text response string, or None on any error.
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
                "--tools", "",
                "--dangerously-skip-permissions",
                "--no-session-persistence",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None
    except (FileNotFoundError, OSError):
        return None

    if proc.returncode != 0 or not proc.stdout.strip():
        return None

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    return extract_result(data)


def extract_result(data: dict) -> str | None:
    """Extract the text result from a `claude -p --output-format json` response."""
    if data.get("is_error"):
        return None
    result = data.get("result", "")
    return result if result else None


def claude_call_json(
    prompt: str,
    json_schema: dict,
    timeout: int = _CLAUDE_TIMEOUT,
    model: str = "haiku",
) -> dict | None:
    """Call `claude -p --json-schema` and return validated structured dict.

    Uses Claude's native schema enforcement — output lands in `structured_output`
    field (not `result`). Eliminates manual JSON parsing and fence stripping.

    Args:
        prompt:      The prompt to send to claude.
        json_schema: JSON Schema dict — Claude's output is validated against this.
        timeout:     Subprocess timeout in seconds (default 15).
        model:       Claude model alias — "haiku" (default), "sonnet", or "opus".

    Returns:
        Validated dict matching the schema, or None on any error.
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
                "--tools", "",
                "--dangerously-skip-permissions",
                "--no-session-persistence",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None
    except (FileNotFoundError, OSError):
        return None

    if proc.returncode != 0 or not proc.stdout.strip():
        return None

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    if data.get("is_error"):
        return None

    structured = data.get("structured_output")
    return structured if isinstance(structured, dict) else None
