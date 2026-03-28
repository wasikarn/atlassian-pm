#!/usr/bin/env python3
"""Tests for hooks/plugin/ai/*.py (claude_call mocked)"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugin.ai.ac_coverage import check_coverage
from plugin.ai.intent_detect import classify_intent
from plugin.ai.intent_detect import main as intent_main
from plugin.ai.path_quality import extract_paths, rate_paths


class TestIntentDetect(unittest.TestCase):

    def test_detects_bug_creation_thai(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value="bug"):
            result = classify_intent("มีบัคใน login ต้องสร้าง ticket")
        self.assertEqual(result, "bug")

    def test_detects_story_creation_english(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value="story"):
            result = classify_intent("I need a user story for the checkout flow")
        self.assertEqual(result, "story")

    def test_returns_none_when_claude_unavailable(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value=None):
            result = classify_intent("create a bug")
        self.assertIsNone(result)

    def test_returns_none_for_unrelated_prompt(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value="none"):
            result = classify_intent("what is the weather today")
        self.assertIsNone(result)

    def test_main_exits_0_on_empty_stdin(self):
        import io
        with patch("sys.stdin", io.StringIO("")), self.assertRaises(SystemExit) as ctx:
            intent_main()
        self.assertEqual(ctx.exception.code, 0)


class TestAcCoverage(unittest.TestCase):

    def test_returns_score_when_claude_responds(self):
        with patch("plugin.ai.ac_coverage.claude_call", return_value="72"):
            score = check_coverage(["AC1: user can login", "AC2: user can logout"],
                                   ["subtask: implement login", "subtask: implement logout"])
        self.assertEqual(score, 72)

    def test_returns_none_when_claude_unavailable(self):
        with patch("plugin.ai.ac_coverage.claude_call", return_value=None):
            score = check_coverage(["AC1"], ["subtask1"])
        self.assertIsNone(score)

    def test_skips_when_no_acs(self):
        score = check_coverage([], ["subtask1"])
        self.assertIsNone(score)

    def test_clamps_score_0_100(self):
        with patch("plugin.ai.ac_coverage.claude_call", return_value="150 out of 100"):
            score = check_coverage(["AC1"], ["subtask1"])
        self.assertEqual(score, 100)

    def test_main_exits_0_when_no_parent_key(self):
        import os
        import subprocess
        stdin_data = json.dumps({
            "tool_input": {"additional_fields": {}},
            "tool_response": {},
            "session_id": "s1"
        })
        result = subprocess.run(
            ["python3", "hooks/plugin/ai/ac_coverage.py"],
            input=stdin_data, capture_output=True, text=True,
            env={**os.environ, "ATLASSIAN_PM_HOOK_DEPTH": "1"},
            cwd=str(Path(__file__).resolve().parents[2])
        )
        self.assertEqual(result.returncode, 0)


class TestPathQuality(unittest.TestCase):

    def test_extract_paths_finds_quoted_files(self):
        text = 'Found `src/auth/login.py` and "lib/utils.ts" in the codebase'
        paths = extract_paths(text)
        self.assertIn("src/auth/login.py", paths)
        self.assertIn("lib/utils.ts", paths)

    def test_returns_poor_rating(self):
        with patch("plugin.ai.path_quality.claude_call", return_value="poor"):
            rating = rate_paths(["src/", "lib/", "utils/"])
        self.assertEqual(rating, "poor")

    def test_returns_none_when_claude_unavailable(self):
        with patch("plugin.ai.path_quality.claude_call", return_value=None):
            rating = rate_paths(["src/"])
        self.assertIsNone(rating)

    def test_skips_when_no_paths(self):
        rating = rate_paths([])
        self.assertIsNone(rating)

    def test_main_exits_0_for_non_task_tool(self):
        import os
        import subprocess
        stdin_data = json.dumps({"tool_name": "Read", "tool_response": "some content", "session_id": "s1"})
        result = subprocess.run(
            ["python3", "hooks/plugin/ai/path_quality.py"],
            input=stdin_data, capture_output=True, text=True,
            env={**os.environ, "ATLASSIAN_PM_HOOK_DEPTH": "1"},
            cwd=str(Path(__file__).resolve().parents[2])
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("{}", result.stdout.strip())

    def test_main_exits_0_for_task_with_poor_paths(self):
        import os
        import subprocess
        stdin_data = json.dumps({
            "tool_name": "Task",
            "tool_response": "Found `src/` and `lib/` directories",
            "session_id": "s1"
        })
        result = subprocess.run(
            ["python3", "hooks/plugin/ai/path_quality.py"],
            input=stdin_data, capture_output=True, text=True,
            env={**os.environ, "ATLASSIAN_PM_HOOK_DEPTH": "1"},
            cwd=str(Path(__file__).resolve().parents[2])
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
