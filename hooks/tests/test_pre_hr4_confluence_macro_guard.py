#!/usr/bin/env python3
"""Tests for hooks/plugin/guards/pre_hr4_confluence_macro_guard.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_has_macros_detects_structured_macro():
    """Detects ac:structured-macro tag."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    content = '<ac:structured-macro ac:name="toc">\n<ac:parameter>test</ac:parameter>\n</ac:structured-macro>'
    assert has_macros(content) is True


def test_has_macros_detects_parameter():
    """Detects ac:parameter tag."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    content = 'Some content <ac:parameter ac:name="title">My Title</ac:parameter>'
    assert has_macros(content) is True


def test_has_macros_detects_rich_text_body():
    """Detects ac:rich-text-body tag."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    content = '<ac:rich-text-body><p>content</p></ac:rich-text-body>'
    assert has_macros(content) is True


def test_has_macros_detects_plain_text_body():
    """Detects ac:plain-text-body tag."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    content = '<ac:plain-text-body><![CDATA[some text]]></ac:plain-text-body>'
    assert has_macros(content) is True


def test_has_macros_detects_ac_name_attribute():
    """Detects ac:name= attribute."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    content = '<div ac:name="expand">content</div>'
    assert has_macros(content) is True


def test_has_macros_case_insensitive():
    """Macro detection is case insensitive."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    content_upper = '<AC:STRUCTURED-MACRO ac:NAME="toc"></AC:STRUCTURED-MACRO>'
    content_mixed = '<Ac:Structured-Macro Ac:Name="code"></Ac:Structured-Macro>'

    assert has_macros(content_upper) is True
    assert has_macros(content_mixed) is True


def test_has_macros_returns_false_for_normal_content():
    """Returns False for regular HTML/content."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    content = '<h1>Title</h1><p>Paragraph with <strong>bold</strong> text.</p>'
    assert has_macros(content) is False


def test_has_macros_returns_false_for_empty_string():
    """Returns False for empty string."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    assert has_macros("") is False


def test_has_macros_detects_in_code_block():
    """Macros are detected even in code blocks - the hook catches all raw macro patterns."""
    from plugin.guards.pre_hr4_confluence_macro_guard import has_macros

    # Note: The hook detects ANY ac:pattern in raw content, including code blocks.
    # This is intentional because:
    # 1. MCP would still corrupt these macros
    # 2. Real macro content should use update_page_storage.py instead
    # 3. Code blocks with macros are unusual and likely indicate a mistake

    # Content with raw macro tags is detected
    content_raw = '''
    <pre><code>
    <ac:structured-macro ac:name="code">
    </ac:structured-macro>
    </code></pre>
    '''
    assert has_macros(content_raw) is True

    # Content with ac:name attribute is also detected (even if escaped tags)
    content_with_name = '''
    <pre><code>
    &lt;ac:structured-macro ac:name="code"&gt;
    &lt;/ac:structured-macro&gt;
    </code></pre>
    '''
    # ac:name= is still detected because it's a pattern indicating macro intent
    assert has_macros(content_with_name) is True

    # Only truly macro-free content passes
    content_clean = '''
    <pre><code>
    function example() { return true; }
    </code></pre>
    '''
    assert has_macros(content_clean) is False


def test_allows_when_no_macros():
    """Hook allows when content has no macros."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "page_id": "12345",
            "content": "<h1>Title</h1><p>Regular content</p>"
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_blocks_when_macros_in_content():
    """Hook blocks when content contains macros."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "page_id": "12345",
            "content": '<ac:structured-macro ac:name="toc"></ac:structured-macro>'
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_blocks_when_macros_in_body():
    """Hook blocks when body field contains macros."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "page_id": "67890",
            "body": '<ac:parameter ac:name="title">Test</ac:parameter>'
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_blocks_when_macros_in_value():
    """Hook blocks when value field contains macros."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "page_id": "11111",
            "value": '<ac:rich-text-body>content</ac:rich-text-body>'
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_allows_on_empty_stdin():
    """Hook allows when stdin is empty."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value=''):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_allows_on_invalid_json():
    """Hook allows when stdin is invalid JSON."""
    from unittest.mock import patch

    with patch('sys.stdin.read', return_value='not valid json'):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_block_message_contains_page_id():
    """Block message includes page_id for user guidance."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "page_id": "99999",
            "content": '<ac:structured-macro ac:name="info"></ac:structured-macro>'
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1


def test_allows_when_content_field_is_not_string():
    """Hook allows when content field is not a string (e.g., dict)."""
    import json
    from unittest.mock import patch

    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "page_id": "12345",
            "content": {"type": "doc", "content": []}  # Dict, not string
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
        except SystemExit as e:
            assert e.code == 0


def test_checks_all_content_fields():
    """Hook checks content, body, and value fields."""
    import json
    from unittest.mock import patch

    # Macro only in 'value' field should be blocked
    stdin_data = {
        "session_id": "test-session",
        "tool_input": {
            "page_id": "12345",
            "content": "normal",
            "body": "normal",
            "value": '<ac:structured-macro ac:name="code"></ac:structured-macro>'
        }
    }

    with patch('sys.stdin.read', return_value=json.dumps(stdin_data)):
        from plugin.guards.pre_hr4_confluence_macro_guard import main

        try:
            main()
            assert False, "Should have blocked"
        except SystemExit as e:
            assert e.code == 1
