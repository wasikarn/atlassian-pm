"""Tests for hooks/plugin/cache_write_invalidate._invalidate_db."""
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path so we can import the hook
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # up to atlassian-pm root


def _make_db(tmp_path):
    db = tmp_path / "jira.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE issues (issue_key TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE searches (cache_key TEXT PRIMARY KEY, result_keys TEXT)")
    conn.execute("CREATE TABLE confluence_pages (page_id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE confluence_sections (section_id TEXT, page_id TEXT)")
    conn.execute("INSERT INTO issues VALUES ('BEP-99')")
    conn.execute("INSERT INTO confluence_pages VALUES ('P1')")
    conn.commit()
    conn.close()
    return db


def test_invalidate_removes_jira_issue(tmp_path):
    db = _make_db(tmp_path)
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(db, issue_key="BEP-99")
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT * FROM issues WHERE issue_key = 'BEP-99'").fetchone()
    assert row is None


def test_invalidate_removes_confluence_page(tmp_path):
    db = _make_db(tmp_path)
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(db, page_id="P1")
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT * FROM confluence_pages WHERE page_id = 'P1'").fetchone()
    assert row is None


def test_invalidate_noop_when_db_missing(tmp_path):
    """Does not raise when DB doesn't exist."""
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(tmp_path / "nonexistent.db", issue_key="BEP-1")  # should not raise


def test_invalidate_noop_when_no_key(tmp_path):
    db = _make_db(tmp_path)
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(db)  # no key or page_id — should be a no-op
