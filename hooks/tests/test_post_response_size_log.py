"""Tests for post_response_size_log hook."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks_state import response_size_get_stats, response_size_track


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    """Use temp directory for state and logs."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    monkeypatch.setattr("hooks_state.STATE_DIR", state_dir)
    monkeypatch.setattr("hooks_state._STATE_STR", str(state_dir))
    monkeypatch.setattr("hooks_lib.LOG_DIR", log_dir)

    # Clear in-process cache
    import hooks_lib
    import hooks_state
    hooks_state._cache.clear()
    hooks_lib.LOG_DIR = log_dir

    yield


def test_response_size_track_accumulates():
    """Test that tracking accumulates per-tool and total stats."""
    session_id = "test-session-1"

    response_size_track(session_id, "jira_get_issue", 1000, 250)
    response_size_track(session_id, "jira_get_issue", 500, 125)
    response_size_track(session_id, "cache_search", 2000, 500)

    stats = response_size_get_stats(session_id)

    assert stats["totals"]["chars"] == 3500
    assert stats["totals"]["tokens"] == 875
    assert stats["totals"]["calls"] == 3

    assert stats["by_tool"]["jira_get_issue"]["chars"] == 1500
    assert stats["by_tool"]["jira_get_issue"]["tokens"] == 375
    assert stats["by_tool"]["jira_get_issue"]["calls"] == 2

    assert stats["by_tool"]["cache_search"]["chars"] == 2000
    assert stats["by_tool"]["cache_search"]["tokens"] == 500
    assert stats["by_tool"]["cache_search"]["calls"] == 1


def test_response_size_track_isolated_sessions():
    """Test that different sessions have isolated stats."""
    response_size_track("session-a", "jira_get_issue", 1000, 250)
    response_size_track("session-b", "cache_search", 2000, 500)

    stats_a = response_size_get_stats("session-a")
    stats_b = response_size_get_stats("session-b")

    assert stats_a["totals"]["chars"] == 1000
    assert stats_a["totals"]["calls"] == 1
    assert "jira_get_issue" in stats_a["by_tool"]

    assert stats_b["totals"]["chars"] == 2000
    assert stats_b["totals"]["calls"] == 1
    assert "cache_search" in stats_b["by_tool"]


def test_response_size_get_stats_empty_session():
    """Test that empty sessions return zero stats."""
    stats = response_size_get_stats("nonexistent-session")

    assert stats["totals"]["chars"] == 0
    assert stats["totals"]["tokens"] == 0
    assert stats["totals"]["calls"] == 0
    assert stats["by_tool"] == {}
