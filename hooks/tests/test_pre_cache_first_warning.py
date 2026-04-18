#!/usr/bin/env python3
"""Tests for hooks/plugin/cache/pre_cache_first_warning.py"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestCacheFirstWarning(unittest.TestCase):
    """Tests for pre_cache_first_warning hook."""

    def setUp(self):
        """Clear test state before each test."""
        state_dir = Path("/tmp/claude-hooks-state")
        if state_dir.exists():
            # Remove test session files
            for f in state_dir.glob("test-session-*"):
                f.unlink()

    def run_hook(self, stdin_data: dict) -> subprocess.CompletedProcess:
        """Run the hook with given stdin data."""
        result = subprocess.run(
            ["python3", "hooks/plugin/cache/pre_cache_first_warning.py"],
            input=json.dumps(stdin_data),
            capture_output=True,
            text=True,
            env={**os.environ, "ATLASSIAN_PM_HOOK_DEPTH": "1"},
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        return result

    def test_exits_0_on_empty_stdin(self):
        """Exit 0 when stdin is empty."""
        result = subprocess.run(
            ["python3", "hooks/plugin/cache/pre_cache_first_warning.py"],
            input="",
            capture_output=True,
            text=True,
            env={**os.environ, "ATLASSIAN_PM_HOOK_DEPTH": "1"},
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        self.assertEqual(result.returncode, 0)

    def test_exits_0_for_non_target_tool(self):
        """Exit 0 for tools not in the target list."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_add_comment",
            "tool_input": {"issue_key": "TP-1", "comment": "test"},
            "session_id": "test-session",
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_exits_0_for_force_refresh(self):
        """Exit 0 without warning when force_refresh=true."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1", "force_refresh": True},
            "session_id": "test-session-force",
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_exits_0_for_use_cache_false(self):
        """Exit 0 without warning when use_cache=false."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_search",
            "tool_input": {"jql": "project = TP", "use_cache": False},
            "session_id": "test-session-nocache",
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_warns_for_jira_get_issue(self):
        """Warn with context injection for jira_get_issue."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1"},
            "session_id": "test-session-warn-1",
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn("cache_get_issue", result.stdout)
        self.assertIn("CACHE-FIRST SUGGESTION", result.stdout)

    def test_warns_for_jira_search(self):
        """Warn with context injection for jira_search."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_search",
            "tool_input": {"jql": "project = TP"},
            "session_id": "test-session-warn-2",
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn("cache_search", result.stdout)
        self.assertIn("CACHE-FIRST SUGGESTION", result.stdout)

    def test_warns_for_jira_get_sprint_issues(self):
        """Warn with context injection for jira_get_sprint_issues."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_sprint_issues",
            "tool_input": {"sprint_id": "123"},
            "session_id": "test-session-warn-3",
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn("cache_sprint_issues", result.stdout)
        self.assertIn("CACHE-FIRST SUGGESTION", result.stdout)

    def test_warning_count_limits_spam(self):
        """Stop warning after 3 warnings in session."""
        session_id = "test-session-spam-limit"

        # First 3 warnings should work
        for i in range(3):
            result = self.run_hook({
                "tool_name": "mcp__mcp-atlassian__jira_get_issue",
                "tool_input": {"issue_key": f"TP-{i}"},
                "session_id": session_id,
            })
            self.assertEqual(result.returncode, 0)
            self.assertIn("CACHE-FIRST SUGGESTION", result.stdout)

        # 4th warning should be skipped
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-99"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
