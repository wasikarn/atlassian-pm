#!/usr/bin/env python3
"""Tests for hooks/plugin/session/post_done_flow_check.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_is_done_transition_exact():
    from plugin.session.post_done_flow_check import is_done_transition
    assert is_done_transition("Done") is True


def test_is_done_transition_case_insensitive():
    from plugin.session.post_done_flow_check import is_done_transition
    assert is_done_transition("DONE") is True
    assert is_done_transition("done") is True


def test_is_done_transition_keywords():
    from plugin.session.post_done_flow_check import is_done_transition
    assert is_done_transition("Close") is True
    assert is_done_transition("Resolve") is True
    assert is_done_transition("Complete") is True


def test_is_done_transition_non_done():
    from plugin.session.post_done_flow_check import is_done_transition
    assert is_done_transition("In Progress") is False
    assert is_done_transition("QA") is False
    assert is_done_transition("Review") is False
    assert is_done_transition("") is False


def test_is_done_transition_negation_prefixes_not_matched():
    from plugin.session.post_done_flow_check import is_done_transition
    assert is_done_transition("Incomplete") is False
    assert is_done_transition("Uncompleted") is False
    assert is_done_transition("Unresolved") is False


def test_is_done_transition_substring_not_matched():
    from plugin.session.post_done_flow_check import is_done_transition
    assert is_done_transition("Disclose") is False
    assert is_done_transition("Disclosed") is False


def test_build_replenish_instruction_contains_required_parts():
    from plugin.session.post_done_flow_check import build_replenish_instruction
    msg = build_replenish_instruction("BEP-42")
    assert "BEP-42" in msg
    assert "/flow-check" in msg
    assert "--replenish" in msg
