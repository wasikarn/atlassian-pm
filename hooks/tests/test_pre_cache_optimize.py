#!/usr/bin/env python3
"""Tests for hooks/plugin/cache/pre_cache_optimize.py (consolidated cache optimization hook)."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestCacheOptimize(unittest.TestCase):
    """Tests for consolidated pre_cache_optimize hook."""

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
            ["python3", "hooks/plugin/cache/pre_cache_optimize.py"],
            input=json.dumps(stdin_data),
            capture_output=True,
            text=True,
            env={**os.environ, "ATLASSIAN_PM_HOOK_DEPTH": "1"},
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        return result

    # ========================================
    # Field preset injection tests
    # ========================================

    def test_field_preset_jira_get_issue(self):
        """Inject default fields for jira_get_issue without fields param."""
        session_id = "test-session-fields-1"
        # Mark cache as checked to prevent blocking by cache_prefer
        from hooks_state import cache_mark_checked
        cache_mark_checked(session_id, "TP-1")

        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertIn("updatedInput", output["hookSpecificOutput"])
        self.assertIn("fields", output["hookSpecificOutput"]["updatedInput"])
        self.assertIn("summary", output["hookSpecificOutput"]["updatedInput"]["fields"])

    def test_field_preset_jira_get_issue_with_fields(self):
        """Do NOT inject fields when already present (but still emit cache warning)."""
        session_id = "test-session-fields-2"
        # Mark cache as checked to prevent blocking by cache_prefer
        from hooks_state import cache_mark_checked
        cache_mark_checked(session_id, "TP-1")

        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1", "fields": "summary,status"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 0)
        # No updatedInput since fields already present, but warning is emitted
        output = json.loads(result.stdout)
        self.assertIn("additionalContext", output["hookSpecificOutput"])
        self.assertNotIn("updatedInput", output["hookSpecificOutput"])

    def test_field_preset_jira_search(self):
        """Inject default fields and limit for jira_search without params."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_search",
            "tool_input": {"jql": "project = TP"},
            "session_id": "test-session-fields-3",
        })
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertIn("updatedInput", output["hookSpecificOutput"])
        self.assertIn("fields", output["hookSpecificOutput"]["updatedInput"])
        self.assertIn("limit", output["hookSpecificOutput"]["updatedInput"])
        self.assertEqual(output["hookSpecificOutput"]["updatedInput"]["limit"], 30)

    def test_field_preset_jira_search_with_limit(self):
        """Inject only fields when limit already present (preserve user's limit)."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_search",
            "tool_input": {"jql": "project = TP", "limit": 10},
            "session_id": "test-session-fields-4",
        })
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertIn("fields", output["hookSpecificOutput"]["updatedInput"])
        # Limit should remain as provided (10), NOT default (30)
        self.assertEqual(output["hookSpecificOutput"]["updatedInput"]["limit"], 10)

    # ========================================
    # Cache preference blocking tests (cache_prefer)
    # ========================================

    def test_blocks_jira_get_issue_without_cache_first(self):
        """Block jira_get_issue if cache not tried first."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1", "fields": "summary"},
            "session_id": "test-session-block-1",
        })
        self.assertEqual(result.returncode, 1)  # Blocked
        self.assertIn("CACHE-FIRST", result.stderr)

    def test_allows_jira_get_issue_after_cache_check(self):
        """Allow jira_get_issue after cache was checked (cache miss)."""
        session_id = "test-session-block-2"
        # First, mark cache as checked for this issue
        from hooks_state import cache_mark_checked
        cache_mark_checked(session_id, "TP-1")

        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1", "fields": "summary"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 0)

    def test_allows_jira_get_issue_with_force_refresh(self):
        """Allow jira_get_issue with force_refresh=true."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1", "force_refresh": True},
            "session_id": "test-session-block-3",
        })
        # Should NOT block, but also should inject fields
        self.assertEqual(result.returncode, 0)

    def test_allows_jira_get_issue_with_use_cache_false(self):
        """Allow jira_get_issue with use_cache=false."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1", "use_cache": False},
            "session_id": "test-session-block-4",
        })
        self.assertEqual(result.returncode, 0)

    # ========================================
    # Cache-first warning tests (cache_first_warning)
    # ========================================

    def test_warns_for_jira_search(self):
        """Warn with context injection for jira_search."""
        # Need cache_checked to not block first
        session_id = "test-session-warn-1"
        from hooks_state import cache_mark_checked
        cache_mark_checked(session_id, "TP-1")  # Prevent blocking

        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_search",
            "tool_input": {"jql": "project = TP"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn("cache_search", result.stdout)

    def test_warns_for_jira_get_sprint_issues(self):
        """Warn with context injection for jira_get_sprint_issues."""
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_sprint_issues",
            "tool_input": {"sprint_id": "123"},
            "session_id": "test-session-warn-2",
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn("cache_sprint_issues", result.stdout)

    def test_warning_count_limits_spam(self):
        """Stop warning after 3 warnings in session."""
        session_id = "test-session-spam-limit"
        from hooks_state import cache_mark_checked

        # First 3 warnings should work
        for i in range(3):
            cache_mark_checked(session_id, f"TP-{i}")  # Prevent blocking
            result = self.run_hook({
                "tool_name": "mcp__mcp-atlassian__jira_get_issue",
                "tool_input": {"issue_key": f"TP-{i}", "fields": "summary"},
                "session_id": session_id,
            })
            self.assertEqual(result.returncode, 0)
            # Check for warning in context (may be in additionalContext)
            if result.stdout.strip():
                output = json.loads(result.stdout)
                self.assertIn("CACHE-FIRST SUGGESTION", output["hookSpecificOutput"].get("additionalContext", ""))

        # 4th warning should be skipped (but field preset may still apply)
        cache_mark_checked(session_id, "TP-99")
        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-99"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 0)
        # Should have field preset but no warning
        if result.stdout.strip():
            output = json.loads(result.stdout)
            # Warning count should not appear
            context = output["hookSpecificOutput"].get("additionalContext", "")
            self.assertNotIn("4/3", context)

    # ========================================
    # Stale read guard tests (hr6_stale_read_guard)
    # ========================================

    def test_blocks_cache_get_issue_with_pending_invalidation(self):
        """Block cache_get_issue when there's a pending invalidation."""
        session_id = "test-session-stale-1"
        from hooks_state import hr6_add_pending
        hr6_add_pending(session_id, "TP-1")

        result = self.run_hook({
            "tool_name": "mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue",
            "tool_input": {"issue_key": "TP-1"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 1)  # Blocked
        self.assertIn("HR6 BLOCKED", result.stderr)

    def test_allows_cache_get_issue_without_pending(self):
        """Allow cache_get_issue when no pending invalidation."""
        result = self.run_hook({
            "tool_name": "mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue",
            "tool_input": {"issue_key": "TP-1"},
            "session_id": "test-session-stale-2",
        })
        self.assertEqual(result.returncode, 0)

    # ========================================
    # Edge cases
    # ========================================

    def test_exits_0_on_empty_stdin(self):
        """Exit 0 when stdin is empty."""
        result = subprocess.run(
            ["python3", "hooks/plugin/cache/pre_cache_optimize.py"],
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
            "session_id": "test-session-non-target",
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_combined_field_preset_and_warning(self):
        """Both field preset injection and warning can occur together."""
        session_id = "test-session-combined"
        from hooks_state import cache_mark_checked
        cache_mark_checked(session_id, "TP-1")  # Prevent blocking

        result = self.run_hook({
            "tool_name": "mcp__mcp-atlassian__jira_get_issue",
            "tool_input": {"issue_key": "TP-1"},
            "session_id": session_id,
        })
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        # Should have updatedInput (field preset)
        self.assertIn("updatedInput", output["hookSpecificOutput"])
        # Should have additionalContext (warning)
        self.assertIn("additionalContext", output["hookSpecificOutput"])


if __name__ == "__main__":
    unittest.main()