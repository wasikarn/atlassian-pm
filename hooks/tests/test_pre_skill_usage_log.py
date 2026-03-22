#!/usr/bin/env python3
"""Tests for pre_skill_usage_log.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_logs_skill_invocation():
    """Should return dict with skill_name, session_id, timestamp."""
    from plugin.session.pre_skill_usage_log import build_record

    record = build_record(
        tool_input={"skill": "create-story", "args": "BEP-10"},
        session_id="sess-123",
        project="atlassian-pm",
    )

    assert record["skill_name"] == "create-story"
    assert record["session_id"] == "sess-123"
    assert record["project"] == "atlassian-pm"
    assert "timestamp" in record


def test_handles_missing_skill_key():
    """Should use empty string for skill_name if key missing."""
    from plugin.session.pre_skill_usage_log import build_record

    record = build_record(
        tool_input={},
        session_id="sess-456",
        project="atlassian-pm",
    )
    assert record["skill_name"] == ""
