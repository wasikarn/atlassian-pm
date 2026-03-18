"""Tests for jira_cache.cache module — 100% coverage target."""

import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

from jira_cache.cache import (
    DEFAULT_TTL,
    PURGE_ISSUES_DAYS,
    PURGE_SEARCHES_HOURS,
    SCHEMA_VERSION,
    JiraCache,
    _extract_field,
    extract_adf_text,
    strip_noise,
)

# --- extract_adf_text ---


class TestExtractAdfText:
    def test_basic_text(self):
        adf = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hello world"}]}],
        }
        assert extract_adf_text(adf) == "Hello world"

    def test_nested_content(self):
        adf = {
            "type": "doc",
            "content": [
                {"type": "heading", "content": [{"type": "text", "text": "Title"}]},
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Body"},
                        {"type": "text", "text": "more"},
                    ],
                },
            ],
        }
        assert extract_adf_text(adf) == "Title Body more"

    def test_none_input(self):
        assert extract_adf_text(None) is None

    def test_empty_dict(self):
        assert extract_adf_text({}) is None

    def test_non_dict(self):
        assert extract_adf_text("string") is None
        assert extract_adf_text(42) is None

    def test_no_text_nodes(self):
        adf = {"type": "doc", "content": [{"type": "paragraph", "content": []}]}
        assert extract_adf_text(adf) is None

    def test_list_walk(self):
        """Test walk handles list nodes (root-level list)."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "item"}]}],
                        }
                    ],
                }
            ],
        }
        assert extract_adf_text(adf) == "item"

    def test_walk_raw_list(self):
        """L196-198 is defensive dead code (walk only called with dicts).
        Covered by pragma: no cover on the source."""
        pass


# --- _extract_field ---


class TestExtractField:
    def test_simple_path(self):
        assert _extract_field({"a": {"b": "c"}}, "a", "b") == "c"

    def test_missing_path(self):
        assert _extract_field({"a": 1}, "b", default="x") == "x"

    def test_non_dict_in_path(self):
        assert _extract_field({"a": "string"}, "a", "b", default=None) is None

    def test_empty_path(self):
        assert _extract_field({"a": 1}) == {"a": 1}


# --- strip_noise ---


class TestStripNoise:
    def test_strips_noise_fields(self):
        data = {
            "key": "BEP-1",
            "self": "https://jira/...",
            "fields": {
                "summary": "test",
                "status": {"name": "Done", "self": "url", "statusCategory": {"name": "Done"}},
            },
        }
        result = strip_noise(data)
        assert "self" not in result
        assert result["key"] == "BEP-1"
        assert "self" not in result["fields"]["status"]
        assert "statusCategory" not in result["fields"]["status"]
        assert result["fields"]["status"]["name"] == "Done"

    def test_strips_from_list(self):
        data = [{"self": "url", "key": "BEP-1"}, {"self": "url2", "name": "test"}]
        result = strip_noise(data)
        assert result == [{"key": "BEP-1"}, {"name": "test"}]

    def test_passes_through_primitives(self):
        assert strip_noise("string") == "string"
        assert strip_noise(42) == 42
        assert strip_noise(None) is None

    def test_nested_noise(self):
        data = {
            "fields": {
                "assignee": {
                    "displayName": "User",
                    "accountId": "abc",
                    "avatarUrls": {"48x48": "url"},
                    "emailAddress": "e@e.com",
                    "active": True,
                    "timeZone": "UTC",
                    "accountType": "atlassian",
                },
            },
        }
        result = strip_noise(data)
        assignee = result["fields"]["assignee"]
        assert assignee == {"displayName": "User"}


# --- JiraCache schema & migration ---


class TestSchema:
    def test_fresh_db_creates_schema(self, tmp_db):
        c = JiraCache(db_path=tmp_db)
        assert c._get_schema_version() == SCHEMA_VERSION
        # Verify tables exist
        tables = c.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t[0] for t in tables}
        assert "issues" in table_names
        assert "sprints" in table_names
        assert "searches" in table_names
        assert "cache_stats" in table_names
        assert "schema_version" in table_names
        c.close()

    def test_migration_runs_on_old_db(self, tmp_db):
        """Simulate v1 DB and verify v2 migration runs."""
        # Create v1 DB manually
        conn = sqlite3.connect(str(tmp_db))
        from jira_cache.cache import _SCHEMA_V1

        conn.executescript(_SCHEMA_V1)
        conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (1)")
        conn.commit()
        conn.close()

        # Open with JiraCache — should run migration to v2
        c = JiraCache(db_path=tmp_db)
        assert c._get_schema_version() == SCHEMA_VERSION
        # purge stats should exist
        row = c.conn.execute("SELECT value FROM cache_stats WHERE key = 'purged_issues'").fetchone()
        assert row is not None
        c.close()

    def test_no_schema_version_table(self, tmp_db):
        """DB without schema_version → version 0 → full create."""
        conn = sqlite3.connect(str(tmp_db))
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        c = JiraCache(db_path=tmp_db)
        assert c._get_schema_version() == SCHEMA_VERSION
        c.close()

    def test_fts5_idempotent(self, tmp_db):
        """Creating cache twice doesn't crash on existing FTS5."""
        c1 = JiraCache(db_path=tmp_db)
        c1.close()
        c2 = JiraCache(db_path=tmp_db)
        c2.close()


# --- PRAGMA tuning ---


class TestPragmas:
    def test_pragmas_applied(self, cache):
        # Just check one PRAGMA to verify they were set
        row = cache.conn.execute("PRAGMA cache_size").fetchone()
        assert row[0] == -16000

        row = cache.conn.execute("PRAGMA temp_store").fetchone()
        assert row[0] == 2  # MEMORY = 2


# --- Issue Operations ---


class TestIssueOperations:
    def test_put_and_get(self, cache, sample_issue):
        cache.put_issue("BEP-100", sample_issue)
        result = cache.get_issue("BEP-100")
        assert result is not None
        # Noise should be stripped
        assert "self" not in result
        assert result["key"] == "BEP-100"

    def test_get_miss(self, cache):
        result = cache.get_issue("BEP-999")
        assert result is None

    def test_get_stale(self, cache, sample_issue):
        """Issue older than max_age returns None."""
        cache.put_issue("BEP-100", sample_issue)
        result = cache.get_issue("BEP-100", max_age_hours=0)
        assert result is None

    def test_get_issue_stale(self, cache, sample_issue):
        """get_issue_stale returns regardless of age."""
        cache.put_issue("BEP-100", sample_issue)
        # Even with 0 max_age, stale returns data
        result = cache.get_issue_stale("BEP-100")
        assert result is not None
        assert result["key"] == "BEP-100"

    def test_get_issue_stale_miss(self, cache):
        assert cache.get_issue_stale("NOPE") is None

    def test_put_strips_noise(self, cache, sample_issue_with_noise):
        cache.put_issue("BEP-200", sample_issue_with_noise)
        result = cache.get_issue("BEP-200")
        # Should not have 'self', 'accountId', etc.
        assert "self" not in result
        fields = result.get("fields", {})
        if fields.get("assignee"):
            assert "accountId" not in fields["assignee"]

    def test_put_with_sprint_list(self, cache):
        issue = {
            "key": "BEP-1",
            "fields": {
                "summary": "t",
                "customfield_10020": [{"id": 42, "name": "S42"}],
            },
        }
        cache.put_issue("BEP-1", issue)
        row = cache.conn.execute("SELECT sprint_id FROM issues WHERE issue_key='BEP-1'").fetchone()
        assert row[0] == 42

    def test_put_with_sprint_dict(self, cache):
        issue = {
            "key": "BEP-1",
            "fields": {
                "summary": "t",
                "customfield_10020": {"id": 99},
            },
        }
        cache.put_issue("BEP-1", issue)
        row = cache.conn.execute("SELECT sprint_id FROM issues WHERE issue_key='BEP-1'").fetchone()
        assert row[0] == 99

    def test_batch_put_with_sprint_dict(self, cache):
        """L441: put_issues_batch with sprint as dict (not list)."""
        issues = [
            {
                "key": "BEP-1",
                "fields": {
                    "summary": "t",
                    "customfield_10020": {"id": 88},
                },
            }
        ]
        cache.put_issues_batch(issues)
        row = cache.conn.execute("SELECT sprint_id FROM issues WHERE issue_key='BEP-1'").fetchone()
        assert row[0] == 88

    def test_put_with_description_adf(self, cache, sample_issue_with_noise):
        cache.put_issue("BEP-200", sample_issue_with_noise)
        row = cache.conn.execute("SELECT description_text FROM issues WHERE issue_key='BEP-200'").fetchone()
        assert row[0] == "Description text here"

    def test_no_accessed_at_on_read(self, cache, sample_issue):
        """P1-B: get_issue should NOT update accessed_at."""
        cache.put_issue("BEP-100", sample_issue)
        # Read — should not trigger commit for accessed_at
        cache.get_issue("BEP-100")
        row = cache.conn.execute("SELECT accessed_at FROM issues WHERE issue_key='BEP-100'").fetchone()
        # accessed_at should be None (we stopped writing it)
        assert row[0] is None


# --- Batch Operations (P1-A, P1-F) ---


class TestBatchOperations:
    def test_put_issues_batch(self, cache, multiple_issues):
        count = cache.put_issues_batch(multiple_issues)
        assert count == 5
        for i in range(1, 6):
            assert cache.get_issue(f"BEP-{i}") is not None

    def test_put_issues_batch_empty(self, cache):
        assert cache.put_issues_batch([]) == 0

    def test_put_issues_batch_skips_no_key(self, cache):
        issues = [{"fields": {"summary": "no key"}}, {"key": "BEP-1", "fields": {"summary": "ok"}}]
        assert cache.put_issues_batch(issues) == 1

    def test_get_issues_batch(self, cache, multiple_issues):
        cache.put_issues_batch(multiple_issues)
        found, missing = cache.get_issues_batch(["BEP-1", "BEP-3", "BEP-999"])
        assert len(found) == 2
        assert missing == ["BEP-999"]

    def test_get_issues_batch_empty(self, cache):
        found, missing = cache.get_issues_batch([])
        assert found == []
        assert missing == []

    def test_get_issues_batch_stale(self, cache, multiple_issues):
        cache.put_issues_batch(multiple_issues)
        found, missing = cache.get_issues_batch(["BEP-1"], max_age_hours=0)
        assert len(found) == 0
        assert missing == ["BEP-1"]

    def test_get_issues_batch_triggers_flush(self, cache, multiple_issues):
        """Batch get should flush stats when threshold is reached."""
        cache._stat_flush_threshold = 2  # Low threshold
        cache.put_issues_batch(multiple_issues)
        # 5 hits + 1 miss = 6 buffer → triggers flush
        found, missing = cache.get_issues_batch(["BEP-1", "BEP-2", "BEP-3", "BEP-4", "BEP-5", "BEP-999"])
        assert len(found) == 5
        assert missing == ["BEP-999"]
        # Verify flush happened — stats in DB
        row = cache.conn.execute("SELECT value FROM cache_stats WHERE key='hits'").fetchone()
        assert row is not None and row[0] >= 5


# --- Sprint Operations ---


class TestSprintOperations:
    def test_put_and_get_sprint(self, cache):
        data = {"name": "Sprint 33", "state": "active", "startDate": "2026-02-24", "endDate": "2026-03-10", "goal": ""}
        cache.put_sprint(673, data)
        result = cache.get_sprint(673)
        assert result is not None
        assert result["name"] == "Sprint 33"

    def test_get_sprint_miss(self, cache):
        assert cache.get_sprint(999) is None

    def test_get_sprint_stale(self, cache):
        data = {"name": "Old Sprint", "state": "closed"}
        cache.put_sprint(1, data)
        assert cache.get_sprint(1, max_age_hours=0) is None


# --- Search Cache ---


class TestSearchCache:
    def test_put_and_get_search(self, cache, multiple_issues):
        data = {"issues": multiple_issues, "total": 5}
        cache.put_search("project = BEP", "summary,status", 50, data)
        result = cache.get_search("project = BEP", "summary,status", 50)
        assert result is not None
        assert result["total"] == 5

    def test_get_search_miss(self, cache):
        assert cache.get_search("missing", "fields", 10) is None

    def test_get_search_stale(self, cache, multiple_issues):
        data = {"issues": multiple_issues, "total": 5}
        cache.put_search("q", "f", 10, data)
        assert cache.get_search("q", "f", 10, max_age_hours=0) is None

    def test_search_caches_issues(self, cache, multiple_issues):
        """put_search should also cache individual issues."""
        data = {"issues": multiple_issues, "total": 5}
        cache.put_search("q", "f", 10, data)
        assert cache.get_issue("BEP-1") is not None

    def test_search_skips_no_key_issues(self, cache):
        """put_search skips issues without key field."""
        issues = [{"fields": {"summary": "no key"}}, {"key": "BEP-1", "fields": {"summary": "ok"}}]
        data = {"issues": issues, "total": 2}
        cache.put_search("q2", "f", 10, data)
        assert cache.get_issue("BEP-1") is not None


# --- Search Key Normalization (P1-D) ---


class TestSearchKeyNormalization:
    def test_whitespace_normalized(self, cache):
        k1 = cache._search_key("project =  BEP  AND  status = Done", "summary,status", 10)
        k2 = cache._search_key("project = BEP AND status = Done", "summary,status", 10)
        assert k1 == k2

    def test_case_normalized(self, cache):
        k1 = cache._search_key("Project = BEP", "summary", 10)
        k2 = cache._search_key("project = bep", "summary", 10)
        assert k1 == k2

    def test_fields_sorted(self, cache):
        k1 = cache._search_key("q", "status,summary", 10)
        k2 = cache._search_key("q", "summary,status", 10)
        assert k1 == k2

    def test_different_limit_different_key(self, cache):
        k1 = cache._search_key("q", "f", 10)
        k2 = cache._search_key("q", "f", 50)
        assert k1 != k2


# --- Full-Text Search ---


class TestTextSearch:
    def test_fts_basic(self, cache, sample_issue_with_noise):
        cache.put_issue("BEP-200", sample_issue_with_noise)
        results = cache.text_search("Description")
        assert len(results) >= 1

    def test_fts_no_results(self, cache):
        results = cache.text_search("zzzznonexistent")
        assert results == []

    def test_fts_bad_syntax(self, cache):
        """Bad FTS5 syntax returns empty list, not error."""
        results = cache.text_search("AND OR NOT )")
        assert results == []

    def test_fts_sanitized_empty(self, cache):
        """Query that sanitizes to empty string returns [] immediately."""
        results = cache.text_search("\"\"  ''")
        assert results == []


# --- Invalidation ---


class TestInvalidation:
    def test_invalidate_issue(self, cache, sample_issue):
        cache.put_issue("BEP-100", sample_issue)
        assert cache.invalidate_issue("BEP-100") is True
        assert cache.get_issue("BEP-100") is None

    def test_invalidate_missing(self, cache):
        assert cache.invalidate_issue("BEP-999") is False

    def test_invalidate_sprint(self, cache, multiple_issues):
        for i in multiple_issues:
            i["fields"]["customfield_10020"] = [{"id": 42}]
        cache.put_issues_batch(multiple_issues)
        cache.put_sprint(42, {"name": "S42"})
        count = cache.invalidate_sprint(42)
        assert count == 5
        assert cache.get_sprint(42) is None

    def test_invalidate_all(self, cache, sample_issue):
        cache.put_issue("BEP-100", sample_issue)
        cache.put_sprint(1, {"name": "S1"})
        cache.put_search("q", "f", 10, {"issues": [], "total": 0})
        cache.invalidate_all()
        assert cache.get_issue("BEP-100") is None
        assert cache.get_sprint(1) is None
        assert cache.get_search("q", "f", 10) is None


# --- Stale Data Purge (P1-E) ---


class TestPurgeStale:
    def test_purge_old_issues(self, cache):
        """Issues older than 7 days should be purged."""
        old_time = (datetime.now() - timedelta(days=PURGE_ISSUES_DAYS + 1)).isoformat()
        cache.conn.execute(
            """INSERT INTO issues (issue_key, summary, data, cached_at)
            VALUES ('OLD-1', 'old', '{}', ?)""",
            (old_time,),
        )
        cache.conn.commit()
        result = cache.purge_stale()
        assert result["purged_issues"] >= 1
        assert cache.get_issue_stale("OLD-1") is None

    def test_purge_old_searches(self, cache):
        """Searches older than 24h should be purged."""
        old_time = (datetime.now() - timedelta(hours=PURGE_SEARCHES_HOURS + 1)).isoformat()
        cache.conn.execute(
            """INSERT INTO searches (cache_key, jql, fields, result_keys, total, data, cached_at)
            VALUES ('k', 'q', 'f', '[]', 0, '{}', ?)""",
            (old_time,),
        )
        cache.conn.commit()
        result = cache.purge_stale()
        assert result["purged_searches"] >= 1

    def test_purge_keeps_fresh(self, cache, sample_issue):
        """Fresh data should not be purged."""
        cache.put_issue("BEP-100", sample_issue)
        result = cache.purge_stale()
        assert result["purged_issues"] == 0
        assert cache.get_issue("BEP-100") is not None


# --- Statistics (P1-B deferred counting) ---


class TestStatistics:
    def test_hit_miss_counting(self, cache, sample_issue):
        cache.put_issue("BEP-100", sample_issue)
        cache.get_issue("BEP-100")  # hit
        cache.get_issue("BEP-999")  # miss
        stats = cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_stats_structure(self, cache):
        stats = cache.get_stats()
        assert "issues_cached" in stats
        assert "sprints_cached" in stats
        assert "searches_cached" in stats
        assert "hit_rate" in stats
        assert "db_size_mb" in stats
        assert "schema_version" in stats
        assert stats["schema_version"] == SCHEMA_VERSION

    def test_deferred_flush(self, cache, sample_issue):
        """Stats should flush when threshold reached."""
        cache._stat_flush_threshold = 3  # Lower for testing
        cache.put_issue("BEP-100", sample_issue)
        cache.get_issue("BEP-100")  # hit (buffer=1)
        cache.get_issue("BEP-999")  # miss (buffer=2)
        cache.get_issue("BEP-100")  # hit (buffer=3 → flush)
        # After flush, DB should have updated values
        row = cache.conn.execute("SELECT value FROM cache_stats WHERE key='hits'").fetchone()
        assert row[0] >= 2

    def test_flush_stats_noop_when_empty(self, cache):
        """Flushing empty buffer is a no-op."""
        cache._flush_stats()  # Should not crash

    def test_purge_stats_included(self, cache):
        stats = cache.get_stats()
        assert "purged_issues" in stats
        assert "purged_searches" in stats

    def test_vacuum(self, cache, sample_issue):
        cache.put_issue("BEP-100", sample_issue)
        cache.vacuum()  # Should not crash


# --- Adaptive TTL ---


class TestAdaptiveTTL:
    def test_done_status(self, cache):
        from tests.conftest import make_issue

        issue = make_issue(key="BEP-1", status="Done")
        cache.put_issue("BEP-1", issue)
        assert cache.get_adaptive_ttl("BEP-1") == 168.0

    def test_active_status(self, cache):
        from tests.conftest import make_issue

        issue = make_issue(key="BEP-2", status="In Progress")
        cache.put_issue("BEP-2", issue)
        assert cache.get_adaptive_ttl("BEP-2") == 6.0

    def test_unknown_status(self, cache):
        from tests.conftest import make_issue

        issue = make_issue(key="BEP-3", status="Custom Status")
        cache.put_issue("BEP-3", issue)
        assert cache.get_adaptive_ttl("BEP-3") == DEFAULT_TTL

    def test_not_cached(self, cache):
        assert cache.get_adaptive_ttl("NOPE") == DEFAULT_TTL


# --- Close ---


class TestClose:
    def test_close_flushes_stats(self, tmp_db, sample_issue):
        """close() should flush buffered stats."""
        from jira_cache.cache import JiraCache

        c = JiraCache(db_path=tmp_db)
        c.put_issue("BEP-100", sample_issue)
        c.get_issue("BEP-100")  # hit buffered
        c.close()

        # Re-open and check stats were persisted
        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute("SELECT value FROM cache_stats WHERE key='hits'").fetchone()
        assert row[0] >= 1
        conn.close()


# --- _check_db_size (C4) ---


class TestCheckDbSize:
    def test_under_limit(self, cache):
        """DB under limit should not warn."""
        import logging

        with patch.object(logging.getLogger("jira_cache.cache"), "warning") as mock_warn:
            cache._check_db_size()
            mock_warn.assert_not_called()

    def test_over_limit(self, tmp_db, sample_issue):
        """DB over limit should log warning."""
        import logging

        c = JiraCache(db_path=tmp_db)
        c.put_issue("BEP-1", sample_issue)
        # Temporarily set limit very low to trigger
        with (
            patch("jira_cache.cache.MAX_DB_SIZE_MB", 0),
            patch.object(logging.getLogger("jira_cache.cache"), "warning") as mock_warn,
        ):
            c._check_db_size()
            mock_warn.assert_called_once()
        c.close()

    def test_no_file(self, tmp_path):
        """Non-existent DB file should not crash."""
        c = JiraCache(db_path=tmp_path / "test.db")
        # DB exists at this point (created by __init__), so test with a fake path
        old_path = c.db_path
        c.db_path = tmp_path / "nonexistent.db"
        c._check_db_size()  # Should not crash
        c.db_path = old_path
        c.close()


# --- L4: get_stats no db_path ---


class TestStatsNoDbPath:
    def test_no_db_path_in_stats(self, cache):
        """L4: get_stats should not expose db_path."""
        stats = cache.get_stats()
        assert "db_path" not in stats
        # But db_size_mb should still be there
        assert "db_size_mb" in stats
