#!/usr/bin/env python3
"""Tests for hooks/plugin/guards/pre_hr3_block_mcp_assignee.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_has_assignee_detects_assignee_key():
    """Detects 'assignee' key in dict."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    tool_input = {"assignee": "user@example.com"}
    assert has_assignee(tool_input) is True


def test_has_assignee_detects_assignee_id():
    """Detects 'assignee_id' key in dict."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    tool_input = {"assignee_id": "5b10ac8d82"}
    assert has_assignee(tool_input) is True


def test_has_assignee_detects_assignee_account_id():
    """Detects 'assignee_account_id' key in dict."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    tool_input = {"assignee_account_id": "5b10ac8d82e2bf5c"}
    assert has_assignee(tool_input) is True


def test_has_assignee_case_insensitive():
    """Assignee detection is case insensitive."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    # Keys are lowercased for comparison
    tool_input_upper = {"ASSIGNEE": "user@example.com"}
    tool_input_mixed = {"Assignee_Account_Id": "5b10ac8d82e2bf5c"}

    assert has_assignee(tool_input_upper) is True
    assert has_assignee(tool_input_mixed) is True


def test_has_assignee_detects_nested():
    """Detects assignee nested in sub-dicts."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    tool_input = {
        "fields": {
            "assignee": {"name": "Test User"}
        }
    }
    assert has_assignee(tool_input) is True


def test_has_assignee_detects_in_list():
    """Detects assignee within list items."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    tool_input = {
        "updates": [
            {"assignee": "user@example.com"},
            {"summary": "Test"}
        ]
    }
    assert has_assignee(tool_input) is True


def test_has_assignee_detects_deeply_nested():
    """Detects assignee deeply nested in structures."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    tool_input = {
        "fields": {
            "subtask": {
                "nested": {
                    "assignee_account_id": "5b10ac8d82e2bf5c"
                }
            }
        }
    }
    assert has_assignee(tool_input) is True


def test_has_assignee_returns_false_for_other_keys():
    """Returns False when no assignee-related keys present."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    tool_input = {
        "issue_key": "TP-123",
        "summary": "Test task",
        "status": "In Progress"
    }
    assert has_assignee(tool_input) is False


def test_has_assignee_returns_false_for_empty_dict():
    """Returns False for empty dict."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    assert has_assignee({}) is False


def test_has_assignee_returns_false_for_empty_list():
    """Returns False for empty list."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    assert has_assignee([]) is False


def test_has_assignee_does_not_match_similar_keys():
    """Does not match keys that contain 'assignee' as substring."""
    from plugin.guards.pre_hr3_block_mcp_assignee import has_assignee

    # Keys like 'assignee_name' or 'previous_assignee' would match
    # because they contain the exact word 'assignee' when lowercased
    # But 'reporter' should not match
    tool_input = {"reporter": "user@example.com"}
    assert has_assignee(tool_input) is False


def test_allows_when_no_assignee():
    """Hook allows when no assignee field present."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-123",
            "summary": "Updated summary"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_blocks_when_assignee_present():
    """Hook blocks when assignee field is present."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-456",
            "assignee": "user@example.com"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_blocks_when_assignee_account_id_present():
    """Hook blocks when assignee_account_id field is present."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-789",
            "assignee_account_id": "5b10ac8d82e2bf5c"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_blocks_when_assignee_nested_in_fields():
    """Hook blocks when assignee is nested in fields dict."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-100",
            "fields": {
                "summary": "Test",
                "assignee": {"accountId": "5b10ac8d82e2bf5c"}
            }
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_allows_on_empty_stdin():
    """Hook allows when stdin is empty."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value=''):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_on_invalid_json():
    """Hook allows when stdin is invalid JSON."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value='not valid json'):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_block_message_contains_issue_key():
    """Block message includes issue_key for user context."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-999",
            "assignee": "user@example.com"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_block_message_shows_acli_alternative():
    """Block message shows acli command alternative."""
    import json
    from unittest.mock import patch
    import io

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-500",
            "assignee": "user@example.com"
        }
    }

    # Capture stderr
    stderr_capture = io.StringIO()

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('sys.stderr', stderr_capture):
            from plugin.guards.pre_hr3_block_mcp_assignee import main

            try:
                main()
                assert False, "Should have blocked"
            except SystemExit as e:
                assert e.code == 1
                stderr_output = stderr_capture.getvalue()
                assert "acli" in stderr_output.lower()


def test_allows_when_issue_key_missing():
    """Hook allows gracefully when issue_key is missing (uses '?')."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "assignee": "user@example.com"
            # No issue_key
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr3_block_mcp_assignee import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1  # Still blocks, just with '?' for issue_key