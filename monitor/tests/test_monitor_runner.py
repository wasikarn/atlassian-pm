"""Tests for monitor/runner.py — run_claude, run_claude_json."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runner import run_claude, run_claude_json

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"


# ── helpers ───────────────────────────────────────────────────────────────────

def _proc(stdout: str, returncode: int = 0) -> MagicMock:
    p = MagicMock()
    p.stdout = stdout
    p.returncode = returncode
    return p


def _ok(result: str) -> str:
    return json.dumps({"result": result, "is_error": False})


def _err() -> str:
    return json.dumps({"result": "", "is_error": True})


def _structured(data: dict) -> str:
    return json.dumps({"structured_output": data, "is_error": False})


SCHEMA = {"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"]}


# ── run_claude ─────────────────────────────────────────────────────────────────

def test_run_claude_returns_result():
    with patch("subprocess.run", return_value=_proc(_ok("analysis done"))):
        assert run_claude("analyze this") == "analysis done"


def test_run_claude_returns_none_on_is_error():
    with patch("subprocess.run", return_value=_proc(_err())):
        assert run_claude("analyze this") is None


def test_run_claude_parses_stdout_on_nonzero_returncode():
    """Official docs: Claude outputs JSON to stdout even on non-zero exit."""
    with patch("subprocess.run", return_value=_proc(_ok("partial"), returncode=1)):
        assert run_claude("analyze this") == "partial"


def test_run_claude_returns_none_on_empty_stdout():
    with patch("subprocess.run", return_value=_proc("")):
        assert run_claude("analyze this") is None


def test_run_claude_returns_none_on_json_decode_error():
    with patch("subprocess.run", return_value=_proc("not json")):
        assert run_claude("analyze this") is None


def test_run_claude_returns_none_on_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=1)):
        assert run_claude("analyze this") is None


def test_run_claude_respects_recursion_guard():
    with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
        with patch("subprocess.run") as mock_run:
            result = run_claude("analyze this")
    assert result is None
    mock_run.assert_not_called()


def test_run_claude_sets_recursion_guard_in_env():
    with patch("subprocess.run", return_value=_proc(_ok("x"))) as mock_run:
        run_claude("prompt")
    env = mock_run.call_args[1]["env"]
    assert env.get(RECURSION_GUARD) == "1"


def test_run_claude_passes_system_prompt():
    """--system-prompt flag appears in cmd when system_prompt is provided."""
    with patch("subprocess.run", return_value=_proc(_ok("x"))) as mock_run:
        run_claude("prompt", system_prompt="You are a monitor assistant.")
    cmd = mock_run.call_args[0][0]
    assert "--system-prompt" in cmd
    idx = cmd.index("--system-prompt")
    assert cmd[idx + 1] == "You are a monitor assistant."


def test_run_claude_no_system_prompt_by_default():
    """--system-prompt flag is NOT in cmd when system_prompt is not provided."""
    with patch("subprocess.run", return_value=_proc(_ok("x"))) as mock_run:
        run_claude("prompt")
    cmd = mock_run.call_args[0][0]
    assert "--system-prompt" not in cmd


# ── run_claude_json ────────────────────────────────────────────────────────────

def test_run_claude_json_returns_structured_output():
    with patch("subprocess.run", return_value=_proc(_structured({"action": "comment"}))):
        assert run_claude_json("analyze this", SCHEMA) == {"action": "comment"}


def test_run_claude_json_returns_none_on_is_error():
    with patch("subprocess.run", return_value=_proc(_err())):
        assert run_claude_json("analyze this", SCHEMA) is None


def test_run_claude_json_returns_none_when_structured_output_missing():
    payload = json.dumps({"result": "some text", "is_error": False})
    with patch("subprocess.run", return_value=_proc(payload)):
        assert run_claude_json("analyze this", SCHEMA) is None


def test_run_claude_json_parses_on_nonzero_returncode():
    with patch("subprocess.run", return_value=_proc(_structured({"action": "skip"}), returncode=1)):
        assert run_claude_json("analyze this", SCHEMA) == {"action": "skip"}


def test_run_claude_json_returns_none_on_empty_stdout():
    with patch("subprocess.run", return_value=_proc("")):
        assert run_claude_json("analyze this", SCHEMA) is None


def test_run_claude_json_passes_json_schema_flag():
    with patch("subprocess.run", return_value=_proc(_structured({"action": "skip"}))) as mock_run:
        run_claude_json("prompt", SCHEMA)
    cmd = mock_run.call_args[0][0]
    assert "--json-schema" in cmd
    assert json.loads(cmd[cmd.index("--json-schema") + 1]) == SCHEMA


def test_run_claude_json_respects_recursion_guard():
    with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
        with patch("subprocess.run") as mock_run:
            result = run_claude_json("prompt", SCHEMA)
    assert result is None
    mock_run.assert_not_called()


def test_run_claude_json_returns_none_on_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=1)):
        assert run_claude_json("prompt", SCHEMA) is None


def test_run_claude_json_passes_system_prompt():
    """--system-prompt flag appears in cmd when system_prompt is provided."""
    with patch("subprocess.run", return_value=_proc(_structured({"action": "skip"}))) as mock_run:
        run_claude_json("prompt", SCHEMA, system_prompt="You are a monitor.")
    cmd = mock_run.call_args[0][0]
    assert "--system-prompt" in cmd
    idx = cmd.index("--system-prompt")
    assert cmd[idx + 1] == "You are a monitor."


def test_run_claude_json_no_system_prompt_by_default():
    """--system-prompt flag is NOT in cmd when system_prompt is not provided."""
    with patch("subprocess.run", return_value=_proc(_structured({"action": "skip"}))) as mock_run:
        run_claude_json("prompt", SCHEMA)
    cmd = mock_run.call_args[0][0]
    assert "--system-prompt" not in cmd
