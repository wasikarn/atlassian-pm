#!/usr/bin/env python3
"""Tests for hooks/plugin/guards/pre_wip_limit_check.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BOARD_CONFIG = {
    "In Progress": {"wip_max": 3, "statuses": ["In Progress", "In Dev"]},
    "Review":      {"wip_max": 2, "statuses": ["Code Review", "Review"]},
    "QA":          {"wip_max": 2, "statuses": ["QA", "Testing"]},
}


def test_find_column_exact_match():
    from plugin.guards.pre_wip_limit_check import find_column
    col_name, cfg = find_column("In Progress", BOARD_CONFIG)
    assert col_name == "In Progress"
    assert cfg["wip_max"] == 3


def test_find_column_alias():
    from plugin.guards.pre_wip_limit_check import find_column
    col_name, cfg = find_column("In Dev", BOARD_CONFIG)
    assert col_name == "In Progress"


def test_find_column_case_insensitive():
    from plugin.guards.pre_wip_limit_check import find_column
    col_name, cfg = find_column("code review", BOARD_CONFIG)
    assert col_name == "Review"


def test_find_column_not_found_returns_none():
    from plugin.guards.pre_wip_limit_check import find_column
    col_name, cfg = find_column("Done", BOARD_CONFIG)
    assert col_name is None
    assert cfg is None


def test_find_column_empty_transition_returns_none():
    from plugin.guards.pre_wip_limit_check import find_column
    col_name, cfg = find_column("", BOARD_CONFIG)
    assert col_name is None


def test_build_block_message_contains_key_info():
    from plugin.guards.pre_wip_limit_check import build_block_message
    msg = build_block_message("BEP-5", "In Progress", 3, "project = \"BEP\" AND status IN (\"In Progress\")")
    assert "In Progress" in msg
    assert "3" in msg
    assert "BEP-5" in msg
    assert "CLAUDE_WIP_CONFIRMED" in msg
    assert "jira_search" in msg
