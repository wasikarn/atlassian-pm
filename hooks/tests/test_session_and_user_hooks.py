#!/usr/bin/env python3
"""Tests for D1 (start_plugin_resources_inject), D3 (user_prompt_mermaid_hint),
and B2 (post_confluence_code_fix_suggest) hooks.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure hooks/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── D1: start_plugin_resources_inject ─────────────────────────────────────


class TestStartPluginResourcesInject:
    """D1: SessionStart plugin resources injection."""

    def _run(self, session_id: str, stdin_data: dict | None = None) -> tuple[str, int]:
        """Run the hook with patched stdin/stdout, return (stdout_output, exit_code)."""
        from io import StringIO
        import importlib

        payload = json.dumps(stdin_data or {"session_id": session_id})

        with patch("sys.stdin", StringIO(payload)), \
             patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            try:
                import plugin.session.start_plugin_resources_inject as mod
                importlib.reload(mod)
                mod.main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code or 0
            output = mock_stdout.getvalue()

        return output, exit_code

    def test_injection_happens_first_call(self, tmp_path, monkeypatch):
        """D1: First call should inject context and create flag file."""
        session_id = "test-session-d1-first"
        monkeypatch.setenv("ATLASSIAN_PM_INTERNAL", "true")

        # Use tmp_path for state dir so we start clean
        state_dir = tmp_path / "claude-hooks-state"
        state_dir.mkdir()

        import plugin.session.start_plugin_resources_inject as mod
        monkeypatch.setattr(mod, "_STATE_DIR", state_dir)

        # Ensure flag doesn't exist
        flag = state_dir / f"{session_id}.resources_injected"
        assert not flag.exists()

        from io import StringIO
        import importlib
        importlib.reload(mod)
        monkeypatch.setattr(mod, "_STATE_DIR", state_dir)

        payload = json.dumps({"session_id": session_id})
        captured = StringIO()
        with patch("sys.stdin", StringIO(payload)), \
             patch("sys.stdout", captured):
            try:
                mod.main()
            except SystemExit:
                pass

        output = captured.getvalue()
        # Should emit a hookSpecificOutput JSON block
        assert output.strip(), "Expected non-empty output on first call"
        data = json.loads(output.strip())
        assert "hookSpecificOutput" in data
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "Plugin Resources" in ctx or "atlassian-pm" in ctx.lower()
        assert "HR5" in ctx or "HR6" in ctx

        # Flag must be written
        assert flag.exists()

    def test_injection_idempotent_second_call(self, tmp_path, monkeypatch):
        """D1: Second call with same session_id must be silent (idempotent)."""
        session_id = "test-session-d1-second"
        monkeypatch.setenv("ATLASSIAN_PM_INTERNAL", "true")

        state_dir = tmp_path / "claude-hooks-state"
        state_dir.mkdir()
        # Pre-create the flag
        (state_dir / f"{session_id}.resources_injected").touch()

        import plugin.session.start_plugin_resources_inject as mod
        import importlib
        importlib.reload(mod)
        monkeypatch.setattr(mod, "_STATE_DIR", state_dir)

        from io import StringIO
        payload = json.dumps({"session_id": session_id})
        captured = StringIO()
        with patch("sys.stdin", StringIO(payload)), \
             patch("sys.stdout", captured):
            try:
                mod.main()
            except SystemExit:
                pass

        # Second call: no output
        assert captured.getvalue().strip() == "", "Expected silent output on second call"


# ── D3: user_prompt_mermaid_hint ──────────────────────────────────────────


class TestUserPromptMermaidHint:
    """D3: UserPromptSubmit mermaid keyword hint."""

    def _run_with_prompt(self, prompt_text: str, monkeypatch) -> tuple[str, int]:
        monkeypatch.setenv("ATLASSIAN_PM_INTERNAL", "true")

        import plugin.user.user_prompt_mermaid_hint as mod
        import importlib
        importlib.reload(mod)

        from io import StringIO
        payload = json.dumps({"session_id": "s1", "prompt": {"text": prompt_text}})
        captured = StringIO()
        with patch("sys.stdin", StringIO(payload)), \
             patch("sys.stdout", captured):
            try:
                mod.main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code or 0

        return captured.getvalue(), exit_code

    def test_mermaid_keyword_triggers_hint(self, monkeypatch):
        """D3: Prompt containing 'mermaid' should inject skill tip."""
        output, _ = self._run_with_prompt("draw a mermaid diagram for this flow", monkeypatch)
        assert output.strip(), "Expected hint output for mermaid prompt"
        data = json.loads(output.strip())
        assert "hookSpecificOutput" in data
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "apm-pretty-mermaid" in ctx
        assert "atlassian-scripts" in ctx

    def test_mermaid_case_insensitive(self, monkeypatch):
        """D3: 'MERMAID' (uppercase) should also trigger."""
        output, _ = self._run_with_prompt("Convert to MERMAID format", monkeypatch)
        assert output.strip()
        data = json.loads(output.strip())
        assert "apm-pretty-mermaid" in data["hookSpecificOutput"]["additionalContext"]

    def test_non_mermaid_prompt_is_silent(self, monkeypatch):
        """D3: Prompt without 'mermaid' must produce no output."""
        output, exit_code = self._run_with_prompt("create a sequence diagram", monkeypatch)
        assert output.strip() == "", "Expected silent output for non-mermaid prompt"
        assert exit_code == 0

    def test_partial_word_not_matched(self, monkeypatch):
        """D3: 'mermaidjs' (no word boundary) must not trigger."""
        output, _ = self._run_with_prompt("use mermaidjs library", monkeypatch)
        # mermaidjs starts with mermaid but \b is between 'd' and 'j' — no match
        assert output.strip() == "", "Expected no hint for 'mermaidjs' (not word-bounded)"


# ── B2: post_confluence_code_fix_suggest ──────────────────────────────────


class TestPostConfluenceCodeFixSuggest:
    """B2: PostToolUse Confluence code-block fix reminder."""

    def _run_with_event(self, tool_name: str, tool_input: dict, monkeypatch) -> tuple[str, int]:
        monkeypatch.setenv("ATLASSIAN_PM_INTERNAL", "true")

        import plugin.quality.post_confluence_code_fix_suggest as mod
        import importlib
        importlib.reload(mod)

        from io import StringIO
        payload = json.dumps({
            "session_id": "s1",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_response": {"success": True},
        })
        captured = StringIO()
        with patch("sys.stdin", StringIO(payload)), \
             patch("sys.stdout", captured):
            try:
                mod.main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code or 0

        return captured.getvalue(), exit_code

    def test_confluence_update_page_injects_reminder(self, monkeypatch):
        """B2: confluence_update_page should inject code-block fix reminder."""
        output, _ = self._run_with_event(
            "confluence_update_page",
            {"page_id": "12345678"},
            monkeypatch,
        )
        assert output.strip(), "Expected reminder output for confluence_update_page"
        data = json.loads(output.strip())
        assert "hookSpecificOutput" in data
        ctx = data["hookSpecificOutput"]["additionalContext"]
        assert "fix_confluence_code_blocks.py" in ctx
        assert "12345678" in ctx
        assert "fix_confluence_panels.py" in ctx

    def test_page_id_extracted_correctly(self, monkeypatch):
        """B2: page_id should appear in the reminder message."""
        output, _ = self._run_with_event(
            "confluence_update_page",
            {"page_id": "99887766"},
            monkeypatch,
        )
        data = json.loads(output.strip())
        assert "99887766" in data["hookSpecificOutput"]["additionalContext"]

    def test_non_confluence_tool_is_silent(self, monkeypatch):
        """B2: Non-confluence tools must produce no output."""
        output, exit_code = self._run_with_event(
            "jira_update_issue",
            {"issue_key": "TP-123"},
            monkeypatch,
        )
        assert output.strip() == "", "Expected silent output for non-confluence tool"
        assert exit_code == 0

    def test_confluence_create_page_is_silent(self, monkeypatch):
        """B2: confluence_create_page (not update) must not trigger."""
        output, _ = self._run_with_event(
            "confluence_create_page",
            {"page_id": "11111"},
            monkeypatch,
        )
        assert output.strip() == "", "Expected silent output for confluence_create_page"
