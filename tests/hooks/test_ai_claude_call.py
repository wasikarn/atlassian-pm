"""Tests for hooks/plugin/ai/claude_call.py — claude_call, claude_call_json, extract_result."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from plugin.ai.claude_call import claude_call, claude_call_json, extract_result

RECURSION_GUARD = "ATLASSIAN_PM_HOOK_DEPTH"


# ── helpers ───────────────────────────────────────────────────────────────────

def _proc(stdout: str, returncode: int = 0) -> MagicMock:
    p = MagicMock()
    p.stdout = stdout
    p.returncode = returncode
    return p


def _ok(result: str) -> str:
    return json.dumps({"result": result, "is_error": False, "subtype": "success"})


def _err() -> str:
    return json.dumps({"result": "", "is_error": True, "subtype": "error"})


def _structured(data: dict) -> str:
    return json.dumps({"structured_output": data, "is_error": False, "subtype": "success"})


# ── extract_result ─────────────────────────────────────────────────────────────

def test_extract_result_returns_text():
    assert extract_result({"result": "hello", "is_error": False}) == "hello"


def test_extract_result_is_error_returns_none():
    assert extract_result({"result": "ignored", "is_error": True}) is None


def test_extract_result_empty_result_returns_none():
    assert extract_result({"result": "", "is_error": False}) is None


def test_extract_result_missing_result_returns_none():
    assert extract_result({"is_error": False}) is None


# ── claude_call ────────────────────────────────────────────────────────────────

def test_claude_call_returns_result_on_success():
    with patch("subprocess.run", return_value=_proc(_ok("intent: bug"))):
        assert claude_call("classify this") == "intent: bug"


def test_claude_call_returns_none_on_is_error():
    with patch("subprocess.run", return_value=_proc(_err())):
        assert claude_call("classify this") is None


def test_claude_call_parses_stdout_on_nonzero_returncode():
    """Official docs: Claude outputs JSON to stdout even on non-zero exit."""
    with patch("subprocess.run", return_value=_proc(_ok("partial"), returncode=1)):
        assert claude_call("classify this") == "partial"


def test_claude_call_returns_none_on_empty_stdout():
    with patch("subprocess.run", return_value=_proc("", returncode=0)):
        assert claude_call("classify this") is None


def test_claude_call_returns_none_on_json_decode_error():
    with patch("subprocess.run", return_value=_proc("not json")):
        assert claude_call("classify this") is None


def test_claude_call_returns_none_on_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=1)):
        assert claude_call("classify this") is None


def test_claude_call_returns_none_on_file_not_found():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert claude_call("classify this") is None


def test_claude_call_respects_recursion_guard():
    with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
        with patch("subprocess.run") as mock_run:
            result = claude_call("classify this")
    assert result is None
    mock_run.assert_not_called()


def test_claude_call_passes_required_flags():
    with patch("subprocess.run", return_value=_proc(_ok("x"))) as mock_run:
        claude_call("prompt", model="sonnet")
    cmd = mock_run.call_args[0][0]
    assert "--tools" in cmd and "" in cmd
    assert "--max-turns" in cmd and "1" in cmd
    assert "--model" in cmd and "sonnet" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert "--no-session-persistence" in cmd
    assert "--output-format" in cmd and "json" in cmd


def test_claude_call_default_model_is_haiku():
    with patch("subprocess.run", return_value=_proc(_ok("x"))) as mock_run:
        claude_call("prompt")
    cmd = mock_run.call_args[0][0]
    idx = cmd.index("--model")
    assert cmd[idx + 1] == "haiku"


def test_claude_call_sets_recursion_guard_in_env():
    with patch("subprocess.run", return_value=_proc(_ok("x"))) as mock_run:
        claude_call("prompt")
    env = mock_run.call_args[1]["env"]
    assert env.get(RECURSION_GUARD) == "1"


# ── claude_call_json ───────────────────────────────────────────────────────────

SCHEMA = {"type": "object", "properties": {"score": {"type": "integer"}}, "required": ["score"]}


def test_claude_call_json_returns_structured_output():
    with patch("subprocess.run", return_value=_proc(_structured({"score": 85}))):
        result = claude_call_json("score this", SCHEMA)
    assert result == {"score": 85}


def test_claude_call_json_returns_none_on_is_error():
    with patch("subprocess.run", return_value=_proc(_err())):
        assert claude_call_json("score this", SCHEMA) is None


def test_claude_call_json_returns_none_when_structured_output_missing():
    payload = json.dumps({"result": "some text", "is_error": False})
    with patch("subprocess.run", return_value=_proc(payload)):
        assert claude_call_json("score this", SCHEMA) is None


def test_claude_call_json_parses_on_nonzero_returncode():
    """Official docs: parse stdout even when exit code != 0."""
    with patch("subprocess.run", return_value=_proc(_structured({"score": 70}), returncode=1)):
        result = claude_call_json("score this", SCHEMA)
    assert result == {"score": 70}


def test_claude_call_json_returns_none_on_empty_stdout():
    with patch("subprocess.run", return_value=_proc("", returncode=0)):
        assert claude_call_json("score this", SCHEMA) is None


def test_claude_call_json_passes_json_schema_flag():
    with patch("subprocess.run", return_value=_proc(_structured({"score": 1}))) as mock_run:
        claude_call_json("prompt", SCHEMA)
    cmd = mock_run.call_args[0][0]
    assert "--json-schema" in cmd
    schema_arg = cmd[cmd.index("--json-schema") + 1]
    assert json.loads(schema_arg) == SCHEMA


def test_claude_call_json_respects_recursion_guard():
    with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
        with patch("subprocess.run") as mock_run:
            result = claude_call_json("prompt", SCHEMA)
    assert result is None
    mock_run.assert_not_called()


def test_claude_call_json_returns_none_on_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=1)):
        assert claude_call_json("prompt", SCHEMA) is None
