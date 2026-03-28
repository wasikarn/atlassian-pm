#!/usr/bin/env python3
"""Shared utility: call `claude -p` for LLM reasoning in hooks and scripts.

Two entry points:
    claude_call()      — returns raw text (str | None); callers parse with parse_json()
    claude_call_json() — uses --json-schema; returns validated dict | None directly

Auth: intentionally NOT using --bare because this plugin runs inside a Claude Code
session that authenticates via OAuth (Claude.ai subscription). --bare disables OAuth
and requires ANTHROPIC_API_KEY. If migrating to a standalone daemon with an API key,
add --bare and remove --dangerously-skip-permissions (use --allowedTools instead).

Recursion guard: sets ATLASSIAN_PM_HOOK_DEPTH=1 in subprocess env.
Any hook that checks this var on entry will skip the AI call,
preventing infinite loops when claude -p fires a new Claude Code session.
"""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_CLAUDE_TIMEOUT = 15  # seconds
_MAX_BUDGET_USD = 0.01  # hooks fire on every event — cap per call


def claude_call(
    prompt: str,
    timeout: int = _CLAUDE_TIMEOUT,
    model: str = "haiku",
    system_prompt: str | None = None,
) -> str | None:
    """Call `claude -p` non-interactively and return the text response.

    Args:
        prompt:        The prompt to send to claude.
        timeout:       Subprocess timeout in seconds (default 15).
        model:         Claude model alias — "haiku" (default), "sonnet", or "opus".
        system_prompt: Optional system prompt passed via --system-prompt.

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
                "--max-budget-usd", str(_MAX_BUDGET_USD),
                "--tools", "",
                "--dangerously-skip-permissions",
                "--no-session-persistence",
                *(["--system-prompt", system_prompt] if system_prompt else []),
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

    # Per official docs: Claude outputs JSON to stdout even on non-zero exit.
    # Always attempt to parse stdout; let is_error flag handle error cases.
    if not proc.stdout.strip():
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
    system_prompt: str | None = None,
) -> dict | None:
    """Call `claude -p --json-schema` and return validated structured dict.

    Uses Claude's native schema enforcement — output lands in `structured_output`
    field (not `result`). Eliminates manual JSON parsing and fence stripping.

    Args:
        prompt:        The prompt to send to claude.
        json_schema:   JSON Schema dict — Claude's output is validated against this.
        timeout:       Subprocess timeout in seconds (default 15).
        model:         Claude model alias — "haiku" (default), "sonnet", or "opus".
        system_prompt: Optional system prompt passed via --system-prompt.

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
                "--max-budget-usd", str(_MAX_BUDGET_USD),
                "--tools", "",
                "--dangerously-skip-permissions",
                "--no-session-persistence",
                *(["--system-prompt", system_prompt] if system_prompt else []),
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
