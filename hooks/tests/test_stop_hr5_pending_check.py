#!/usr/bin/env python3
"""Tests for stop_hr5_pending_check.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_ok_when_no_pending():
    """Returns ok=true when no subtasks are pending verification."""
    from plugin.session.stop_hr5_pending_check import check_pending

    result = check_pending(pending=[])
    assert result == {"ok": True}


def test_blocked_when_pending():
    """Returns ok=false with child key in reason when subtasks unverified."""
    from plugin.session.stop_hr5_pending_check import check_pending

    result = check_pending(pending=[{"child": "TP-42", "parent": "TP-10"}, {"child": "TP-43", "parent": "TP-10"}])
    assert result["ok"] is False
    assert "TP-42" in result["reason"] and "TP-43" in result["reason"]
