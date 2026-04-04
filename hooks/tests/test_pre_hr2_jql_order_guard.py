#!/usr/bin/env python3
"""Tests for hooks/plugin/guards/pre_hr2_jql_order_guard.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_parent_regex_matches_equals():
    """PARENT_RE matches 'parent=' pattern."""
    from plugin.guards.pre_hr2_jql_order_guard import PARENT_RE

    assert PARENT_RE.search("parent = TP-123") is not None
    assert PARENT_RE.search("parent=TP-123") is not None


def test_parent_regex_matches_in_clause():
    """PARENT_RE matches 'parent in (...)' pattern."""
    from plugin.guards.pre_hr2_jql_order_guard import PARENT_RE

    assert PARENT_RE.search("parent in (TP-1, TP-2)") is not None
    assert PARENT_RE.search("parent IN (TP-123)") is not None


def test_parent_regex_case_insensitive():
    """PARENT_RE is case insensitive."""
    from plugin.guards.pre_hr2_jql_order_guard import PARENT_RE

    assert PARENT_RE.search("PARENT = TP-123") is not None
    assert PARENT_RE.search("Parent IN (TP-1)") is not None


def test_parent_regex_does_not_match_parent_keyword():
    """PARENT_RE does not match unrelated 'parent' usage."""
    from plugin.guards.pre_hr2_jql_order_guard import PARENT_RE

    # These should not match because they don't have = or in following
    assert PARENT_RE.search("parentKey = TP-123") is None
    assert PARENT_RE.search("parentKey = TP-123") is None  # parentKey != parent\b


def test_order_by_regex_matches():
    """ORDER_BY_RE matches various ORDER BY patterns."""
    from plugin.guards.pre_hr2_jql_order_guard import ORDER_BY_RE

    assert ORDER_BY_RE.search("ORDER BY created") is not None
    assert ORDER_BY_RE.search("ORDER  BY priority DESC") is not None
    assert ORDER_BY_RE.search("order by key") is not None
    assert ORDER_BY_RE.search("Order By status ASC") is not None


def test_order_by_regex_case_insensitive():
    """ORDER_BY_RE is case insensitive."""
    from plugin.guards.pre_hr2_jql_order_guard import ORDER_BY_RE

    assert ORDER_BY_RE.search("order by created") is not None
    assert ORDER_BY_RE.search("ORDER BY created") is not None
    assert ORDER_BY_RE.search("Order By created") is not None


def test_allows_when_no_jql():
    """Hook allows when JQL is not present."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "issue_key": "TP-123"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_when_jql_empty():
    """Hook allows when JQL is empty string."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": ""
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_jql_without_parent():
    """Hook allows JQL without 'parent' keyword."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "project = TP ORDER BY created DESC"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_jql_without_order_by():
    """Hook allows JQL with parent but without ORDER BY."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "parent = TP-123"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_blocks_jql_with_parent_and_order_by():
    """Hook blocks JQL with both 'parent' and 'ORDER BY'."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "parent = TP-123 ORDER BY created DESC"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_blocks_jql_with_parent_in_and_order_by():
    """Hook blocks JQL with 'parent in (...)' and 'ORDER BY'."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "parent in (TP-1, TP-2, TP-3) ORDER BY priority"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_blocks_case_insensitive():
    """Hook blocks regardless of case."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "PARENT = TP-123 order by created"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_uses_query_field_as_alternative():
    """Hook checks both 'jql' and 'query' fields."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "query": "parent = TP-123 ORDER BY created"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_allows_when_jql_is_none():
    """Hook allows when JQL is None."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": None
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_on_empty_stdin():
    """Hook allows when stdin is empty."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value=''):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_on_invalid_json():
    """Hook allows when stdin is invalid JSON."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value='not valid json'):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_blocks_complex_jql():
    """Hook blocks complex JQL with parent and ORDER BY."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "project = TP AND parent = EP-1 AND status = 'In Progress' ORDER BY priority DESC, created ASC"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_allows_jql_with_other_order_by():
    """Hook allows ORDER BY on queries without parent."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "jql": "project = TP AND status = 'In Progress' ORDER BY priority DESC"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr2_jql_order_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0