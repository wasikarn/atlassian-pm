#!/usr/bin/env python3
"""Tests for hook aggregator framework."""
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aggregator import _extract_contexts, _run_hook


@pytest.fixture
def temp_hook_dir():
    """Create a temporary directory for test hook scripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_run_hook_pattern_a_allow(temp_hook_dir):
    """Test running Pattern A hook (has main()) that allows."""
    hook_file = temp_hook_dir / "test_hook_a.py"
    hook_file.write_text("""
import sys

def main():
    print("Hook A ran")
    sys.exit(0)

if __name__ == "__main__":
    main()
""")

    result = _run_hook(hook_file, "")
    assert result.exit_code == 0
    assert "Hook A ran" in result.stdout


def test_run_hook_pattern_b_block(temp_hook_dir):
    """Test running Pattern B hook (top-level logic) that blocks."""
    hook_file = temp_hook_dir / "test_hook_b.py"
    hook_file.write_text("""
import sys

print("Hook B error", file=sys.stderr)
sys.exit(1)
""")

    result = _run_hook(hook_file, "")
    assert result.exit_code == 1
    assert "Hook B error" in result.stderr


def test_run_hook_with_stdin(temp_hook_dir):
    """Test hook receives stdin data."""
    hook_file = temp_hook_dir / "test_hook_stdin.py"
    hook_file.write_text("""
import json
import sys

data = json.load(sys.stdin)
print(f"Got: {data.get('key')}")
sys.exit(0)
""")

    stdin_data = json.dumps({"key": "value"})
    result = _run_hook(hook_file, stdin_data)
    assert result.exit_code == 0
    assert "Got: value" in result.stdout


def test_extract_contexts_single():
    """Test extracting single inject_context JSON from stdout."""
    stdout = json.dumps({
        "hookSpecificOutput": {
            "additionalContext": "context1"
        }
    })

    contexts = _extract_contexts(stdout)
    assert len(contexts) == 1
    assert "context1" in contexts[0]


def test_extract_contexts_multiple():
    """Test extracting multiple inject_context JSONs from stdout."""
    line1 = json.dumps({
        "hookSpecificOutput": {
            "additionalContext": "context1"
        }
    })
    line2 = json.dumps({
        "hookSpecificOutput": {
            "additionalContext": "context2"
        }
    })
    stdout = f"{line1}\n{line2}"

    contexts = _extract_contexts(stdout)
    assert len(contexts) == 2
    assert "context1" in contexts[0]
    assert "context2" in contexts[1]


def test_extract_contexts_empty():
    """Test extracting contexts from empty output."""
    contexts = _extract_contexts("")
    assert len(contexts) == 0


def test_run_hook_pattern_b_with_import(temp_hook_dir):
    """Test Pattern B hook that imports a local helper module."""
    # Use a name that won't conflict with real modules in sys.modules
    lib_file = temp_hook_dir / "_test_helper_lib.py"
    lib_file.write_text("""
def helper():
    return "helper result"
""")

    hook_file = temp_hook_dir / "test_hook_import.py"
    hook_file.write_text("""
import sys
sys.path.insert(0, ".")
from _test_helper_lib import helper

print(helper())
sys.exit(0)
""")

    # Change to temp dir for import to work
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(temp_hook_dir)
        result = _run_hook(hook_file, "")
        assert result.exit_code == 0
        assert "helper result" in result.stdout
    finally:
        os.chdir(old_cwd)


def test_run_hook_nonexistent_file():
    """Test running hook on nonexistent file."""
    result = _run_hook(Path("/nonexistent/hook.py"), "")
    # Should handle gracefully by catching exception
    assert result.exit_code == 2


def test_extract_contexts_malformed_json():
    """Test that malformed JSON is gracefully skipped."""
    stdout = "not json\n" + json.dumps({
        "hookSpecificOutput": {
            "additionalContext": "context1"
        }
    })

    contexts = _extract_contexts(stdout)
    # Should extract the valid JSON, ignore the invalid line
    assert len(contexts) == 1
    assert "context1" in contexts[0]


def test_run_hook_pattern_a_with_exception(temp_hook_dir):
    """Test Pattern A hook that raises exception in main()."""
    hook_file = temp_hook_dir / "test_hook_exception.py"
    hook_file.write_text("""
def main():
    raise ValueError("test error")

if __name__ == "__main__":
    main()
""")

    result = _run_hook(hook_file, "")
    # Should catch exception and return exit code 2
    assert result.exit_code == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
