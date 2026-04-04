#!/usr/bin/env python3
"""Tests for hooks/plugin/guards/pre_hr6_stale_read_guard.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_allows_when_no_issue_key():
    """Hook allows when no issue key can be extracted."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "project = TP"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr6_stale_read_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_when_no_pending_invalidation():
    """Hook allows when no pending invalidation for the issue."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-123"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value=set()):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
            except SystemExit as e:
                assert e.code == 0


def test_allows_when_issue_not_in_pending():
    """Hook allows when requested issue is not in pending set."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-999"
        }
    }

    # TP-123 is pending, but we're requesting TP-999
    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-123", "TP-456"}):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
            except SystemExit as e:
                assert e.code == 0


def test_blocks_when_issue_in_pending():
    """Hook blocks when requested issue has pending invalidation."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-123"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-123"}):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
                assert False, "Should have blocked"
            except SystemExit as e:
                assert e.code == 1


def test_blocks_case_insensitive():
    """Hook blocks regardless of issue key case."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "tp-123"  # lowercase
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-123"}):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
                assert False, "Should have blocked"
            except SystemExit as e:
                assert e.code == 1


def test_uses_issue_key_or_id_field():
    """Hook also checks issue_key_or_id field."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key_or_id": "TP-789"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-789"}):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
                assert False, "Should have blocked"
            except SystemExit as e:
                assert e.code == 1


def test_uses_key_field():
    """Hook also checks 'key' field."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "key": "TP-456"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-456"}):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
                assert False, "Should have blocked"
            except SystemExit as e:
                assert e.code == 1


def test_allows_on_empty_stdin():
    """Hook allows when stdin is empty."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value=''):
        from plugin.guards.pre_hr6_stale_read_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_on_invalid_json():
    """Hook allows when stdin is invalid JSON."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value='not valid json'):
        from plugin.guards.pre_hr6_stale_read_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_block_message_shows_invalidation_hint():
    """Block message tells user to run cache_invalidate."""
    import json
    import io
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-123"
        }
    }

    stderr_capture = io.StringIO()

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-123"}):
            with patch('sys.stderr', stderr_capture):
                from plugin.guards.pre_hr6_stale_read_guard import main

                try:
                    main()
                    assert False, "Should have blocked"
                except SystemExit as e:
                    assert e.code == 1
                    stderr_output = stderr_capture.getvalue()
                    assert "cache_invalidate" in stderr_output
                    assert "TP-123" in stderr_output


def test_blocks_with_multiple_pending():
    """Hook blocks when issue is one of multiple pending."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-456"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-123", "TP-456", "TP-789"}):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
                assert False, "Should have blocked"
            except SystemExit as e:
                assert e.code == 1


def test_allows_with_multiple_pending_different_issue():
    """Hook allows when requesting issue not in pending set."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-999"  # Not in pending
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-123", "TP-456"}):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
            except SystemExit as e:
                assert e.code == 0


def test_get_issue_key_extracts_from_tool_input():
    """get_issue_key helper extracts issue key correctly."""
    from hooks_lib import get_issue_key

    # Test issue_key field
    assert get_issue_key({"issue_key": "tp-123"}) == "TP-123"

    # Test issue_key_or_id field
    assert get_issue_key({"issue_key_or_id": "tp-456"}) == "TP-456"

    # Test key field
    assert get_issue_key({"key": "tp-789"}) == "TP-789"

    # Test priority: issue_key > issue_key_or_id > key
    assert get_issue_key({"issue_key": "TP-1", "key": "TP-2"}) == "TP-1"

    # Test None when no key found
    assert get_issue_key({"summary": "Test"}) is None


def test_allows_when_session_id_missing():
    """Hook allows when session_id is missing (graceful degradation)."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "tool_input": {
            "issue_key": "TP-123"
        }
        # No session_id
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value=set()):
            from plugin.guards.pre_hr6_stale_read_guard import main

            try:
                main()
            except SystemExit as e:
                assert e.code == 0


def test_logs_on_allow():
    """Hook logs ALLOWED event when allowing."""
    import json
    from unittest.mock import patch, MagicMock

    stdin_data = {
        "session_id": "test-session-log",
        "tool_input": {
            "issue_key": "TP-123"
        }
    }

    mock_log = MagicMock()

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value=set()):
            with patch('plugin.guards.pre_hr6_stale_read_guard.log_event', mock_log):
                from plugin.guards.pre_hr6_stale_read_guard import main

                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0
                    # Check that log_event was called with ALLOWED
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][0] == "hr6-read-guard"
                    assert call_args[0][1] == "ALLOWED"


def test_logs_on_block():
    """Hook logs BLOCKED event when blocking."""
    import json
    from unittest.mock import patch, MagicMock

    stdin_data = {
        "session_id": "test-session-block",
        "tool_input": {
            "issue_key": "TP-123"
        }
    }

    mock_log = MagicMock()

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr6_stale_read_guard.hr6_get_pending', return_value={"TP-123"}):
            with patch('plugin.guards.pre_hr6_stale_read_guard.log_event', mock_log):
                from plugin.guards.pre_hr6_stale_read_guard import main

                try:
                    main()
                    assert False, "Should have blocked"
                except SystemExit as e:
                    assert e.code == 1
                    # Check that log_event was called with BLOCKED
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][0] == "hr6-read-guard"
                    assert call_args[0][1] == "BLOCKED"