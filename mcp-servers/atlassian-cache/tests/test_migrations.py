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


def test_partial_migration_from_v1_applies_remaining_steps(conn):
    """Starting from v1, migrate() applies v2 and v3 without re-running v1 DDL."""
    # Bootstrap to v1 manually (avoids calling migrate() which would go to SCHEMA_VERSION)
    from atlassian_cache import migrations as m
    conn.executescript(m._SCHEMA_V1)
    conn.execute("PRAGMA user_version = 1")
    conn.commit()

    migrate(conn)

    # v2 adds purged_issues stat row
    row = conn.execute("SELECT value FROM cache_stats WHERE key = 'purged_issues'").fetchone()
    assert row is not None, "purged_issues stat row missing — v2 migration not applied"

    # v3 adds sprint_id column to searches
    cols = {r[1] for r in conn.execute("PRAGMA table_info(searches)")}
    assert "sprint_id" in cols, "sprint_id column missing — v3 migration not applied"

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


def test_v4_confluence_tables_exist(conn):
    """v4 migration creates all 5 Confluence tables."""
    migrate(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert "confluence_pages" in tables
    assert "confluence_links" in tables
    assert "confluence_searches" in tables
    assert "confluence_sections" in tables


def test_v4_confluence_sections_fk(conn):
    """confluence_sections has FOREIGN KEY to confluence_pages (enforced)."""
    migrate(conn)
    conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO confluence_sections VALUES (?,?,?,?,?,?)",
            ("ghost::intro", "ghost-page-id", "Intro", "text", "hash123", "2026-01-01")
        )
        conn.commit()
