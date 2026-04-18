import json
import time
from concurrent.futures import ProcessPoolExecutor

import pytest

from hooks.hooks_state import (
    _get_connection,
    get_state,
    hr6_add_pending,
    hr6_clear_all_pending,
    hr6_get_pending,
    hr6_remove_pending,
    set_state,
)

# --- 1. WAL Concurrency Testing ---

def _worker_write(args):
    session_id, key, value = args
    try:
        set_state(session_id, key, value)
    except Exception as e:
        return e
    return True

def test_wal_concurrency(temp_state_dir, session_id):
    """Spawn parallel processes to verify no lock contention or corruption."""
    num_workers = 20
    iterations = 20

    # Prepare data for workers: each worker writes to its own key
    tasks = [(session_id, f"key_{i}", i) for i in range(num_workers)]

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for _ in range(iterations):
            results = list(executor.map(_worker_write, tasks))
            for res in results:
                if isinstance(res, Exception):
                    pytest.fail(f"Worker failed with exception: {res}")

    # Verify all keys were written correctly
    for i in range(num_workers):
        assert get_state(session_id, f"key_{i}") == i

# --- 2. Migration Path Testing ---

def test_migration_path(temp_state_dir, session_id):
    """Verify migration from .json state to SQLite."""
    json_file = temp_state_dir / f"{session_id}.json"

    # Mock old JSON state
    mock_data = {
        "user_pref": {"value": "dark-mode", "ts": time.time()},
        "hr6_pending": ["key1", "key2"],
        "hr5_pending": [
            {"child": "C1", "parent": "P1", "ts": time.time()},
            {"child": "C2", "parent": "P2", "ts": time.time()},
        ],
        "hr5_known_subtasks": ["K1", "K2"]
    }
    json_file.write_text(json.dumps(mock_data))

    # Trigger migration
    # Use a fresh connection to trigger _migrate_from_json
    conn = _get_connection(session_id)
    conn.close()

    # Verify data migrated to SQLite
    # Note: get_state uses the Bloom Filter. If the migration doesn't update
    # the Bloom Filter, get_state will return None.
    # The current hooks_state.py _migrate_from_json does NOT update the BF.
    # This is a bug we've discovered via testing.
    assert get_state(session_id, "user_pref") == "dark-mode"
    assert "key1" in hr6_get_pending(session_id)
    assert "key2" in hr6_get_pending(session_id)

    # Verify JSON was archived
    assert not json_file.exists()
    assert (temp_state_dir / f"{session_id}.json.bak").exists()

# --- 3. L1 Cache Consistency ---

def test_l1_cache_consistency(temp_state_dir, session_id):
    """Verify that set_state correctly invalidates the lru_cache of get_state."""
    key = "cache_test"
    val1 = "initial"
    val2 = "updated"

    set_state(session_id, key, val1)
    assert get_state(session_id, key) == val1

    set_state(session_id, key, val2)
    assert get_state(session_id, key) == val2

# --- 4. State Expiry ---

def test_state_expiry(temp_state_dir, session_id, monkeypatch):
    """Verify that expired state returns None."""
    from hooks.hooks_state import STATE_EXPIRY_SECONDS

    key = "expiry_test"
    set_state(session_id, key, "alive")

    now = time.time()
    def mock_time():
        return now + STATE_EXPIRY_SECONDS + 1

    monkeypatch.setattr("time.time", mock_time)
    assert get_state(session_id, key) is None

# --- 5. HR6 Logic Tests ---

def test_hr6_lifecycle(temp_state_dir, session_id):
    """Test the full lifecycle of HR6 pending keys."""
    key = "test_key"

    hr6_add_pending(session_id, key)
    assert key in hr6_get_pending(session_id)

    hr6_remove_pending(session_id, key)
    assert key not in hr6_get_pending(session_id)

    hr6_add_pending(session_id, "k1")
    hr6_add_pending(session_id, "k2")
    hr6_clear_all_pending(session_id)
    assert len(hr6_get_pending(session_id)) == 0
