#!/usr/bin/env python3
"""Tests for hooks/plugin/ai/claude_call.py"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugin.ai.claude_call import RECURSION_GUARD, claude_call, extract_result


class TestClaudeCall(unittest.TestCase):

    def _make_proc(self, stdout: str, returncode: int = 0) -> MagicMock:
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        m.stderr = ""
        return m

    def test_returns_result_on_success(self):
        payload = json.dumps({
            "type": "result", "subtype": "success",
            "is_error": False, "result": "hello", "session_id": "s1"
        })
        with patch("subprocess.run", return_value=self._make_proc(payload)):
            result = claude_call("say hello")
        self.assertEqual(result, "hello")

    def test_sets_recursion_guard_env(self):
        payload = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "ok"})
        captured_env = {}

        def fake_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return self._make_proc(payload)

        with patch("subprocess.run", side_effect=fake_run):
            claude_call("test")
        self.assertEqual(captured_env.get(RECURSION_GUARD), "1")

    def test_returns_none_when_recursion_guard_set(self):
        with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 15)):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_when_claude_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_on_nonzero_exit(self):
        with patch("subprocess.run", return_value=self._make_proc("", returncode=1)):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_returns_none_on_invalid_json(self):
        with patch("subprocess.run", return_value=self._make_proc("not json")):
            result = claude_call("test")
        self.assertIsNone(result)

    def test_extract_result_from_json(self):
        data = {"type": "result", "subtype": "success", "is_error": False, "result": "answer"}
        self.assertEqual(extract_result(data), "answer")

    def test_extract_result_returns_none_on_error(self):
        data = {"type": "result", "subtype": "error", "is_error": True, "result": ""}
        self.assertIsNone(extract_result(data))


if __name__ == "__main__":
    unittest.main()
