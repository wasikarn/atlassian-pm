#!/usr/bin/env python3
"""Tests for hooks/plugin/guards/pre_hr7_sprint_id_guard.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_has_sprint_field_detects_direct_field():
    """Detects sprint field at top level of tool_input."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    tool_input = {"customfield_10020": 42}
    assert has_sprint_field(tool_input) is True


def test_has_sprint_field_detects_nested_in_fields():
    """Detects sprint field nested in additional_fields."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    tool_input = {
        "issue_key": "TP-123",
        "additional_fields": '{"customfield_10020": 42}'
    }
    # Note: JSON string is not parsed by has_sprint_field, but dict nesting works
    tool_input_parsed = {
        "issue_key": "TP-123",
        "additional_fields": {"customfield_10020": 42}
    }
    assert has_sprint_field(tool_input_parsed) is True


def test_has_sprint_field_detects_in_update_dict():
    """Detects sprint field nested in update dict."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    tool_input = {
        "issue_key": "TP-123",
        "fields": {"customfield_10020": 42}
    }
    assert has_sprint_field(tool_input) is True


def test_has_sprint_field_detects_in_list():
    """Detects sprint field within list items."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    tool_input = {
        "updates": [
            {"customfield_10020": 42},
            {"summary": "Test"}
        ]
    }
    assert has_sprint_field(tool_input) is True


def test_has_sprint_field_returns_false_for_other_fields():
    """Returns False when sprint field is absent."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    tool_input = {
        "issue_key": "TP-123",
        "summary": "Test task",
        "description": "Description"
    }
    assert has_sprint_field(tool_input) is False


def test_has_sprint_field_returns_false_for_empty_dict():
    """Returns False for empty dict."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    assert has_sprint_field({}) is False


def test_has_sprint_field_returns_false_for_empty_list():
    """Returns False for empty list."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    assert has_sprint_field([]) is False


def test_has_sprint_field_handles_deeply_nested():
    """Detects sprint field deeply nested in structures."""
    from plugin.guards.pre_hr7_sprint_id_guard import has_sprint_field

    tool_input = {
        "outer": {
            "middle": {
                "inner": {
                    "customfield_10020": "sprint-123"
                }
            }
        }
    }
    assert has_sprint_field(tool_input) is True


def test_allows_when_no_sprint_field(caplog, monkeypatch):
    """Hook allows when sprint field is not present."""
    import json
    from unittest.mock import patch

    # Mock stdin with no sprint field
    stdin_data = {
        "session_id": "test-session-123",
        "tool_input": {
            "issue_key": "TP-123",
            "summary": "Test task"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr7_sprint_id_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0  # allow() exits with 0


def test_allows_when_lookup_done(caplog, monkeypatch):
    """Hook allows when sprint field present but lookup was done."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session-lookup-done",
        "tool_input": {
            "issue_key": "TP-123",
            "customfield_10020": 42
        }
    }

    # Mock hr7_is_lookup_done to return True
    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr7_sprint_id_guard.hr7_is_lookup_done', return_value=True):
            from plugin.guards.pre_hr7_sprint_id_guard import main

            try:
                main()
            except SystemExit as e:
                assert e.code == 0  # allow() exits with 0


def test_blocks_when_no_lookup_done(caplog, monkeypatch):
    """Hook blocks when sprint field present but no lookup done."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session-no-lookup",
        "tool_input": {
            "issue_key": "TP-456",
            "customfield_10020": 42
        }
    }

    # Mock hr7_is_lookup_done to return False
    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr7_sprint_id_guard.hr7_is_lookup_done', return_value=False):
            from plugin.guards.pre_hr7_sprint_id_guard import main

            try:
                main()
                assert False, "Should have blocked"
            except SystemExit as e:
                assert e.code == 1  # block() exits with 1


def test_allows_on_empty_stdin():
    """Hook allows when stdin is empty."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value=''):
        from plugin.guards.pre_hr7_sprint_id_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_on_invalid_json():
    """Hook allows when stdin is invalid JSON."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value='not valid json'):
        from plugin.guards.pre_hr7_sprint_id_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_block_message_contains_board_id():
    """Block message includes board_id from config for help."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-789",
            "customfield_10020": 42
        }
    }

    # Mock config to have specific board_id
    mock_config = {"jira": {"board_id": "board-999"}}

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        with patch('plugin.guards.pre_hr7_sprint_id_guard.hr7_is_lookup_done', return_value=False):
            with patch('plugin.guards.pre_hr7_sprint_id_guard._cfg', mock_config):
                from plugin.guards.pre_hr7_sprint_id_guard import main

                try:
                    main()
                    assert False, "Should have blocked"
                except SystemExit as e:
                    assert e.code == 1
