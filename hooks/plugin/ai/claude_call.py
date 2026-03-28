#!/usr/bin/env python3
"""Shared utility: call `claude -p` for LLM reasoning in hooks and scripts.

Usage:
    from plugin.ai.claude_call import claude_call

    result = claude_call("classify this intent: create a bug for login failure")
    if result:
        print(result)

Recursion guard: sets ATLASSIAN_PM_HOOK_DEPTH=1 in subprocess env.
Any hook that checks this var on entry will skip the AI call,
preventing infinite loops when claude -p fires a new Claude Code session.
"""

import json
import os
import subprocess

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"
_CLAUDE_TIMEOUT = 15  # seconds

try:
    from hooks_state import load_state, save_state
    _HAS_STATE = True
except ImportError:
    _HAS_STATE = False


def _track_cost(cost: float) -> None:
    """Accumulate AI call cost in session state. Never raises."""
    if not _HAS_STATE or not cost:
        return
    try:
        state = load_state()
        state["session_ai_cost_usd"] = state.get("session_ai_cost_usd", 0.0) + cost
        state["session_ai_calls"] = state.get("session_ai_calls", 0) + 1
        save_state(state)
    except Exception:
        pass  # Never let cost tracking break the main flow


def claude_call(prompt: str, timeout: int = _CLAUDE_TIMEOUT) -> str | None:
    """Call `claude -p` non-interactively and return the text response.

    Args:
        prompt:  The prompt to send to claude.
        timeout: Subprocess timeout in seconds (default 15).

    Returns:
        The text response string, or None on any error.
    """
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

    _track_cost(data.get("total_cost_usd", 0.0))
    return extract_result(data)


def extract_result(data: dict) -> str | None:
    """Extract the text result from a `claude -p --output-format json` response."""
    if data.get("is_error"):
        return None
    result = data.get("result", "")
    return result if result else None
