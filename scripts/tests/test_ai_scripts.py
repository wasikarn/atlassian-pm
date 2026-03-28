#!/usr/bin/env python3
"""Tests for scripts/ai/*.py (claude -p mocked)"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.claude_runner import RECURSION_GUARD, run_claude
from ai.enrich_description import build_enrich_prompt, parse_adf_from_response
from ai.pre_qg_polish import build_polish_prompt, parse_polished_adf
from ai.suggest_subtasks import build_subtask_prompt, parse_subtasks_from_response


class TestClaudeRunner(unittest.TestCase):

    def _make_proc(self, stdout: str, returncode: int = 0) -> MagicMock:
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        m.stderr = ""
        return m

    def test_returns_text_on_success(self):
        payload = json.dumps({"type": "result", "subtype": "success",
                               "is_error": False, "result": "hello"})
        with patch("subprocess.run", return_value=self._make_proc(payload)):
            result = run_claude("say hello")
        self.assertEqual(result, "hello")

    def test_recursion_guard_skips(self):
        with patch.dict(os.environ, {RECURSION_GUARD: "1"}):
            result = run_claude("test")
        self.assertIsNone(result)

    def test_returns_none_on_failure(self):
        with patch("subprocess.run", return_value=self._make_proc("", returncode=1)):
            result = run_claude("test")
        self.assertIsNone(result)


class TestEnrichDescription(unittest.TestCase):

    def test_build_prompt_contains_text(self):
        prompt = build_enrich_prompt("user needs login feature", "story")
        self.assertIn("user needs login feature", prompt)
        self.assertIn("story", prompt.lower())

    def test_parse_adf_extracts_json_block(self):
        response = '```json\n{"version": 1, "type": "doc", "content": []}\n```'
        result = parse_adf_from_response(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "doc")

    def test_parse_adf_returns_none_on_invalid(self):
        result = parse_adf_from_response("no json here")
        self.assertIsNone(result)


class TestSuggestSubtasks(unittest.TestCase):

    def test_build_prompt_contains_acs(self):
        prompt = build_subtask_prompt("TP-100", ["AC1: user can login", "AC2: user can logout"])
        self.assertIn("AC1", prompt)
        self.assertIn("AC2", prompt)

    def test_parse_subtasks_from_numbered_list(self):
        response = "1. Implement login endpoint\n2. Add logout button\n3. Write integration tests"
        result = parse_subtasks_from_response(response)
        self.assertEqual(len(result), 3)
        self.assertIn("Implement login endpoint", result[0])

    def test_parse_subtasks_returns_empty_on_invalid(self):
        result = parse_subtasks_from_response("")
        self.assertEqual(result, [])


class TestPreQgPolish(unittest.TestCase):

    def test_build_polish_prompt_contains_adf(self):
        adf = {"version": 1, "type": "doc", "content": []}
        prompt = build_polish_prompt(json.dumps(adf), "story")
        self.assertIn('"type": "doc"', prompt)

    def test_parse_polished_adf_extracts_json(self):
        adf = {"version": 1, "type": "doc", "content": [{"type": "paragraph"}]}
        response = f'```json\n{json.dumps(adf)}\n```'
        result = parse_polished_adf(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "doc")

    def test_parse_polished_adf_returns_none_on_garbage(self):
        result = parse_polished_adf("cannot improve this")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
