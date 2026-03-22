#!/usr/bin/env python3
"""Tests for stop_hr5_pending_check.py"""
import json
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

    result = check_pending(pending=[{"child": "BEP-42", "parent": "BEP-10"}, {"child": "BEP-43", "parent": "BEP-10"}])
    assert result["ok"] is False
    assert "BEP-42" in result["reason"] or "BEP-43" in result["reason"]
