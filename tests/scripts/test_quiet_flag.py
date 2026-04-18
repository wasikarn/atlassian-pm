"""Smoke tests: verify --quiet flag appears in --help output for high-use CLI scripts."""

import subprocess
import sys

SCRIPTS = [
    "scripts/api/update_page_storage.py",
    "scripts/api/fix_confluence_code_blocks.py",
    "scripts/api/fix_confluence_panels.py",
    "scripts/api/move_confluence_page.py",
    "scripts/api/jira_batch_update.py",
]


def _help_text(script: str) -> str:
    result = subprocess.run(
        [sys.executable, script, "--help"],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def test_update_page_storage_quiet_in_help():
    assert "--quiet" in _help_text("scripts/api/update_page_storage.py")


def test_fix_confluence_code_blocks_quiet_in_help():
    assert "--quiet" in _help_text("scripts/api/fix_confluence_code_blocks.py")


def test_fix_confluence_panels_quiet_in_help():
    assert "--quiet" in _help_text("scripts/api/fix_confluence_panels.py")


def test_move_confluence_page_quiet_in_help():
    assert "--quiet" in _help_text("scripts/api/move_confluence_page.py")


def test_jira_batch_update_quiet_in_help():
    assert "--quiet" in _help_text("scripts/api/jira_batch_update.py")
