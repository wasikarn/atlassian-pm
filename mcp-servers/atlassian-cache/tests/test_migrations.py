"""Tests for atlassian_cache.migrations — 100% coverage."""
import sqlite3
import pytest
from atlassian_cache.migrations import SCHEMA_VERSION, migrate


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "m.db"
    c = sqlite3.connect(str(db), check_same_thread=False)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_fresh_db_reaches_current_version(conn):
    """A fresh DB migrates all the way to SCHEMA_VERSION."""
    migrate(conn)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_migrate_is_idempotent(conn):
    """Calling migrate() twice is safe."""
    migrate(conn)
    migrate(conn)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_user_version_matches_constant(conn):
    """user_version after migration equals SCHEMA_VERSION constant."""
    migrate(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_partial_migration_failure_rolls_back(conn):
    """If a migration step raises, the DB stays at prior version."""
    from atlassian_cache import migrations as m
    original_v2 = m._MIGRATIONS[2]
    m._MIGRATIONS[2] = "THIS IS INVALID SQL;"
    try:
        with pytest.raises(sqlite3.OperationalError):
            migrate(conn)
        # DB should still be at version 1 (v2 failed)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == 1
    finally:
        m._MIGRATIONS[2] = original_v2


def test_issues_table_exists_after_migration(conn):
    """Core issues table is created by migration."""
    migrate(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "issues" in tables
    assert "sprints" in tables
    assert "searches" in tables
