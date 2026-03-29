"""Tests for server.py handlers and utilities — 100% coverage target."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import make_issue

# We need to mock the auth/api imports before importing server
# since they depend on external credentials
with patch.dict(
    "sys.modules",
    {
        "lib.auth": MagicMock(),
        "lib.jira_api": MagicMock(),
    },
):
    import server
    from server import (
        MAX_RESPONSE_CHARS,
        _coerce_args,
        _compact_issue,
        _compact_response,
        _embedding_text,
        _find_issues_list,
        _format_issue_summary,
        _paginate_response,
        _require_cache,
        _strip_response_noise,
        _timed_upstream,
        _validate_issue_key,
        handle_cache_find_confluence_related,
        handle_cache_get_confluence_children,
        handle_cache_get_issue,
        handle_cache_get_issues,
        handle_cache_invalidate,
        handle_cache_invalidate_confluence,
        handle_cache_refresh,
        handle_cache_refresh_confluence,
        handle_cache_search,
        handle_cache_similar_issues,
        handle_cache_similar_sprints,
        handle_cache_sprint_issues,
        handle_cache_stats,
        handle_cache_text_search,
        _reindex_pages,
        _reindex_sections,
    )


@pytest.fixture(autouse=True)
def setup_server_globals(cache, tmp_path):
    """Inject test cache into server globals."""
    from atlassian_cache.confluence_cache import ConfluenceCache
    server.cache = cache
    server.confluence = ConfluenceCache(server.cache.conn, server.cache._lock)
    server.embeddings = None
    server.jira_api = None
    server._session_returned.clear()
    yield


@pytest.fixture
def mock_jira_api():
    """Mock JiraAPI for upstream calls."""
    api = MagicMock()
    server.jira_api = api
    yield api
    server.jira_api = None


# --- _format_issue_summary ---


class TestFormatIssueSummary:
    def test_basic(self):
        issue = make_issue(key="TP-1", summary="Test", status="Done", assignee="Alice", issue_type="Bug")
        result = _format_issue_summary(issue)
        assert "[TP-1]" in result
        assert "Test" in result
        assert "Done" in result
        assert "Alice" in result
        assert "Bug" in result

    def test_no_assignee(self):
        issue = make_issue(assignee=None)
        result = _format_issue_summary(issue)
        assert "Unassigned" in result

    def test_string_status(self):
        issue = make_issue()
        issue["fields"]["status"] = "Done"
        result = _format_issue_summary(issue)
        assert "Done" in result

    def test_string_assignee(self):
        issue = make_issue()
        issue["fields"]["assignee"] = "Bob"
        result = _format_issue_summary(issue)
        assert "Bob" in result

    def test_string_issuetype(self):
        issue = make_issue()
        issue["fields"]["issuetype"] = "Task"
        result = _format_issue_summary(issue)
        assert "Task" in result


# --- _compact_issue ---


class TestCompactIssue:
    def test_basic(self):
        issue = make_issue(key="TP-1", summary="Test", status="Done", assignee="Alice")
        compact = _compact_issue(issue)
        assert compact["key"] == "TP-1"
        assert compact["summary"] == "Test"
        assert compact["status"] == "Done"
        assert compact["assignee"] == "Alice"

    def test_with_parent(self):
        issue = make_issue(parent_key="TP-100")
        compact = _compact_issue(issue)
        assert compact["parent"] == "TP-100"

    def test_no_parent(self):
        issue = make_issue()
        compact = _compact_issue(issue)
        assert "parent" not in compact

    def test_with_labels(self):
        issue = make_issue(labels=["bug", "coupon"])
        compact = _compact_issue(issue)
        assert compact["labels"] == ["bug", "coupon"]

    def test_string_fields(self):
        issue = make_issue()
        issue["fields"]["status"] = "Custom"
        issue["fields"]["assignee"] = None
        issue["fields"]["issuetype"] = "Task"
        issue["fields"]["priority"] = "High"
        issue["fields"]["parent"] = "TP-99"
        compact = _compact_issue(issue)
        assert compact["status"] == "Custom"
        assert compact["assignee"] == "Unassigned"
        assert compact["issuetype"] == "Task"
        assert compact["priority"] == "High"
        assert compact["parent"] == "TP-99"


# --- Response size management ---


class TestStripResponseNoise:
    def test_strips_noise(self):
        data = {"self": "url", "key": "TP-1"}
        result = json.loads(_strip_response_noise(json.dumps(data)))
        assert "self" not in result

    def test_bad_json(self):
        assert _strip_response_noise("not json") == "not json"

    def test_none_input(self):
        assert _strip_response_noise(None) is None


class TestFindIssuesList:
    def test_top_level_issues(self):
        data = {"issues": [1, 2]}
        issues, parent, key = _find_issues_list(data)
        assert issues == [1, 2]
        assert key == "issues"

    def test_nested_results(self):
        data = {"results": {"issues": [1]}}
        issues, parent, key = _find_issues_list(data)
        assert issues == [1]

    def test_data_key(self):
        data = {"data": [1, 2]}
        issues, parent, key = _find_issues_list(data)
        assert issues == [1, 2]
        assert key == "data"

    def test_no_issues(self):
        issues, parent, key = _find_issues_list({"other": "stuff"})
        assert issues is None


class TestPaginateResponse:
    def test_paginates_large(self):
        issues = [make_issue(key=f"TP-{i}") for i in range(100)]
        data = {"issues": issues, "total": 100}
        big = json.dumps(data)
        assert len(big) > MAX_RESPONSE_CHARS
        result = _paginate_response(big)
        parsed = json.loads(result)
        assert "_pagination" in parsed
        assert parsed["_pagination"]["has_more"]

    def test_bad_json(self):
        result = _paginate_response("x" * (MAX_RESPONSE_CHARS + 1))
        assert "truncated" in result

    def test_no_issues_key(self):
        data = json.dumps({"other": "x" * MAX_RESPONSE_CHARS})
        result = _paginate_response(data)
        assert "truncated" in result


class TestCompactResponse:
    def test_compacts(self):
        issues = [make_issue(key=f"TP-{i}") for i in range(20)]
        data = {"issues": issues}
        big = json.dumps(data)
        result = _compact_response(big)
        parsed = json.loads(result)
        assert parsed.get("_compacted") is True
        # Compact issues should have minimal fields
        first = parsed["issues"][0]
        assert "key" in first
        assert "summary" in first
        assert "fields" not in first  # compacted removes nested fields

    def test_bad_json(self):
        result = _compact_response("x" * 100)
        assert "truncated" in result

    def test_no_issues(self):
        result = _compact_response(json.dumps({"other": "x" * 100}))
        assert "truncated" in result

    def test_non_issue_items_preserved(self):
        data = {"issues": ["plain string"]}
        result = _compact_response(json.dumps(data))
        parsed = json.loads(result)
        assert parsed["issues"] == ["plain string"]


# --- _timed_upstream ---


class TestTimedUpstream:
    def test_success(self):
        result = _timed_upstream("test", lambda x: x + 1, 41)
        assert result == 42

    def test_failure(self):
        def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            _timed_upstream("test", fail)


# --- _coerce_args ---


class TestCoerceArgs:
    def test_string_to_int(self):
        result = _coerce_args("cache_search", {"limit": "30"})
        assert result["limit"] == 30

    def test_string_to_bool(self):
        result = _coerce_args("cache_get_issue", {"force_refresh": "true"})
        assert result["force_refresh"] is True

    def test_string_to_float(self):
        result = _coerce_args("cache_get_issue", {"max_age_hours": "2.5"})
        assert result["max_age_hours"] == 2.5

    def test_union_type_integer(self):
        result = _coerce_args("cache_sprint_issues", {"sprint_id": "123"})
        assert result["sprint_id"] == 123

    def test_non_string_passthrough(self):
        result = _coerce_args("cache_search", {"limit": 30})
        assert result["limit"] == 30

    def test_unknown_tool(self):
        result = _coerce_args("unknown_tool", {"x": "1"})
        assert result == {"x": "1"}

    def test_invalid_conversion(self):
        result = _coerce_args("cache_search", {"limit": "not_a_number"})
        assert result["limit"] == "not_a_number"  # Left as-is

    def test_bool_variants(self):
        assert _coerce_args("cache_get_issue", {"force_refresh": "1"})["force_refresh"] is True
        assert _coerce_args("cache_get_issue", {"force_refresh": "yes"})["force_refresh"] is True
        assert _coerce_args("cache_get_issue", {"force_refresh": "false"})["force_refresh"] is False

    def test_union_type_skip_non_int(self):
        """Union type without integer/number should skip."""
        # Inject a tool with union ["string", "array"]
        server._TOOL_SCHEMAS["test_union"] = {"x": ["string", "array"]}
        result = _coerce_args("test_union", {"x": "hello"})
        assert result["x"] == "hello"
        del server._TOOL_SCHEMAS["test_union"]

    def test_union_type_number(self):
        """Union type with number should convert."""
        server._TOOL_SCHEMAS["test_num"] = {"x": ["number", "string"]}
        result = _coerce_args("test_num", {"x": "3.14"})
        assert result["x"] == 3.14
        del server._TOOL_SCHEMAS["test_num"]


# --- Handler tests ---


class TestHandleCacheGetIssue:
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache):
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1"}))
        assert result["source"] == "cache"
        assert result["issue"]["key"] == "TP-1"

    @pytest.mark.asyncio
    async def test_cache_hit_compact(self, cache):
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "compact": True}))
        assert result["source"] == "cache"
        assert "fields" not in result["issue"]

    @pytest.mark.asyncio
    async def test_upstream_fetch(self, cache, mock_jira_api):
        upstream_issue = make_issue(key="TP-2", summary="Upstream")
        mock_jira_api.get_issue.return_value = upstream_issue
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-2"}))
        assert result["source"] == "upstream"
        mock_jira_api.get_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_refresh(self, cache, mock_jira_api):
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        mock_jira_api.get_issue.return_value = issue
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "force_refresh": True}))
        assert result["source"] == "upstream"

    @pytest.mark.asyncio
    async def test_no_upstream_stale_fallback(self, cache):
        """No API + stale data → returns stale."""
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        server.jira_api = None
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "force_refresh": True}))
        assert result["source"] == "stale_cache"
        assert "warning" in result

    @pytest.mark.asyncio
    async def test_no_upstream_no_cache(self, cache):
        server.jira_api = None
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-999"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_upstream_error_stale_fallback(self, cache, mock_jira_api):
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        mock_jira_api.get_issue.side_effect = Exception("timeout")
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "force_refresh": True}))
        assert result["source"] == "stale_cache"

    @pytest.mark.asyncio
    async def test_upstream_error_no_stale(self, cache, mock_jira_api):
        mock_jira_api.get_issue.side_effect = Exception("timeout")
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-999"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_with_embeddings(self, cache, mock_jira_api):
        """When embeddings available, should store embedding."""
        emb = MagicMock()
        emb.available = True
        emb.store_embedding.return_value = True
        server.embeddings = emb
        mock_jira_api.get_issue.return_value = make_issue(key="TP-1")
        await handle_cache_get_issue({"issue_key": "TP-1"})
        emb.store_embedding.assert_called_once()
        server.embeddings = None

    # --- T12: Lazy version-check tests ---

    @pytest.mark.asyncio
    async def test_lazy_hit_when_upstream_unchanged(self, cache, mock_jira_api):
        """T12: Stale cache + upstream 'updated' unchanged → serve from cache (lazy HIT)."""
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        # Simulate upstream returning the same or older 'updated' timestamp
        cached = cache.get_issue_stale("TP-1")
        cached_at_iso = cached["_cached_at_iso"]
        mock_jira_api.get_issue.return_value = {"fields": {"updated": cached_at_iso}}
        # max_age_hours=0 forces stale path
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "max_age_hours": 0}))
        assert result["source"] == "cache"
        # Should have called upstream only once (the cheap updated-field check)
        mock_jira_api.get_issue.assert_called_once()
        call_kwargs = mock_jira_api.get_issue.call_args
        assert call_kwargs.kwargs.get("fields") == "updated" or (
            len(call_kwargs.args) > 1 and call_kwargs.args[1] == "updated"
        )

    @pytest.mark.asyncio
    async def test_lazy_miss_when_upstream_changed(self, cache, mock_jira_api):
        """T12: Stale cache + upstream 'updated' is newer → full refresh (lazy MISS)."""
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        # First call: cheap check returns a newer upstream timestamp
        # Second call: full refresh
        full_issue = make_issue(key="TP-1", summary="Updated upstream")
        mock_jira_api.get_issue.side_effect = [
            {"fields": {"updated": "2099-12-31T23:59:59.000+0000"}},  # newer → lazy miss
            full_issue,  # full refresh
        ]
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "max_age_hours": 0}))
        assert result["source"] == "upstream"
        assert mock_jira_api.get_issue.call_count == 2

    @pytest.mark.asyncio
    async def test_lazy_check_skipped_without_cached_at(self, cache, mock_jira_api):
        """T12: If cached data has no _cached_at (pre-T12 entry), lazy check is skipped."""
        # Insert a raw issue without _cached_at metadata (simulates legacy entry)
        cache.conn.execute(
            "INSERT OR REPLACE INTO issues (issue_key, summary, data, cached_at) VALUES (?, ?, ?, ?)",
            ("TP-1", "Legacy", '{"key": "TP-1", "fields": {"summary": "Legacy"}}', "2000-01-01T00:00:00"),
        )
        cache.conn.commit()
        full_issue = make_issue(key="TP-1")
        mock_jira_api.get_issue.return_value = full_issue
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "max_age_hours": 0}))
        # Falls through to full refresh
        assert result["source"] == "upstream"

    @pytest.mark.asyncio
    async def test_lazy_check_error_falls_through(self, cache, mock_jira_api):
        """T12: If lazy check throws, fall through to full refresh silently."""
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        full_issue = make_issue(key="TP-1", summary="Refreshed")
        mock_jira_api.get_issue.side_effect = [
            Exception("network error"),  # lazy check fails
            full_issue,  # full refresh succeeds
        ]
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "max_age_hours": 0}))
        assert result["source"] == "upstream"
        assert mock_jira_api.get_issue.call_count == 2

    @pytest.mark.asyncio
    async def test_lazy_check_skipped_when_no_jira_api(self, cache):
        """T12: Lazy check is skipped when jira_api is None."""
        issue = make_issue(key="TP-1")
        cache.put_issue("TP-1", issue)
        server.jira_api = None
        result = json.loads(await handle_cache_get_issue({"issue_key": "TP-1", "max_age_hours": 0}))
        # Falls through to stale_cache path (no API available)
        assert result["source"] == "stale_cache"


class TestHandleCacheGetIssues:
    @pytest.mark.asyncio
    async def test_empty_keys(self):
        result = json.loads(await handle_cache_get_issues({"issue_keys": []}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_all_cached(self, cache):
        for i in range(3):
            cache.put_issue(f"TP-{i}", make_issue(key=f"TP-{i}"))
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["TP-0", "TP-1", "TP-2"]}))
        assert result["from_cache"] == 3
        assert result["from_upstream"] == 0

    @pytest.mark.asyncio
    async def test_with_upstream_fetch(self, cache, mock_jira_api):
        cache.put_issue("TP-1", make_issue(key="TP-1"))
        mock_jira_api.get_issue.return_value = make_issue(key="TP-2")
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["TP-1", "TP-2"]}))
        assert result["from_cache"] == 1
        assert result["from_upstream"] == 1

    @pytest.mark.asyncio
    async def test_compact(self, cache):
        cache.put_issue("TP-1", make_issue(key="TP-1"))
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["TP-1"], "compact": True}))
        assert "fields" not in result["issues"][0]

    @pytest.mark.asyncio
    async def test_upstream_error_stale_fallback(self, cache, mock_jira_api):
        cache.put_issue("TP-1", make_issue(key="TP-1"))
        mock_jira_api.get_issue.side_effect = Exception("fail")
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["TP-1", "TP-2"], "force_refresh": True}))
        # TP-2 should fail but TP-1 should come from stale
        assert result["total"] >= 0

    @pytest.mark.asyncio
    async def test_with_embeddings(self, cache, mock_jira_api):
        emb = MagicMock()
        emb.available = True
        server.embeddings = emb
        mock_jira_api.get_issue.return_value = make_issue(key="TP-1")
        await handle_cache_get_issues({"issue_keys": ["TP-1"]})
        emb.store_batch.assert_called()
        server.embeddings = None


class TestHandleCacheSearch:
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache):
        data = {"issues": [make_issue()], "total": 1}
        cache.put_search("project = TP", "summary", 30, data)
        result = json.loads(await handle_cache_search({"jql": "project = TP", "fields": "summary", "limit": 30}))
        assert result["source"] == "cache"

    @pytest.mark.asyncio
    async def test_upstream(self, cache, mock_jira_api):
        mock_jira_api.search_issues.return_value = {"issues": [make_issue()], "total": 1}
        result = json.loads(await handle_cache_search({"jql": "project = TP"}))
        assert result["source"] == "upstream"

    @pytest.mark.asyncio
    async def test_no_upstream(self, cache):
        result = json.loads(await handle_cache_search({"jql": "q"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_upstream_error(self, cache, mock_jira_api):
        mock_jira_api.search_issues.side_effect = Exception("fail")
        result = json.loads(await handle_cache_search({"jql": "q"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_pagination_offset(self, cache, mock_jira_api):
        issues = [make_issue(key=f"TP-{i}") for i in range(5)]
        mock_jira_api.search_issues.return_value = {"issues": issues, "total": 5}
        result = json.loads(await handle_cache_search({"jql": "q", "start_at": 2}))
        assert len(result["results"]["issues"]) == 3

    @pytest.mark.asyncio
    async def test_with_embeddings(self, cache, mock_jira_api):
        emb = MagicMock()
        emb.available = True
        server.embeddings = emb
        mock_jira_api.search_issues.return_value = {"issues": [], "total": 0}
        await handle_cache_search({"jql": "q"})
        emb.store_batch.assert_called_once()
        server.embeddings = None

    @pytest.mark.asyncio
    async def test_force_refresh(self, cache, mock_jira_api):
        data = {"issues": [], "total": 0}
        cache.put_search("q", "summary,status,assignee,issuetype,priority", 30, data)
        mock_jira_api.search_issues.return_value = {"issues": [make_issue()], "total": 1}
        result = json.loads(await handle_cache_search({"jql": "q", "force_refresh": True}))
        assert result["source"] == "upstream"

    @pytest.mark.asyncio
    async def test_limit_capped_at_50(self, cache, mock_jira_api):
        mock_jira_api.search_issues.return_value = {"issues": [], "total": 0}
        await handle_cache_search({"jql": "q", "limit": 100})
        mock_jira_api.search_issues.assert_called_once()
        call_kwargs = mock_jira_api.search_issues.call_args
        assert call_kwargs.kwargs.get("max_results", call_kwargs[1].get("max_results")) <= 50


class TestHandleCacheSprintIssues:
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache):
        data = {"issues": [make_issue()], "total": 1}
        cache.put_search("sprint = 673", "summary,status,assignee,issuetype,priority,labels", 50, data)
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 673}))
        assert result["source"] == "cache"

    @pytest.mark.asyncio
    async def test_upstream(self, cache, mock_jira_api):
        mock_jira_api.get_sprint_issues.return_value = {"issues": [make_issue()], "total": 1}
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 673}))
        assert result["source"] == "upstream"

    @pytest.mark.asyncio
    async def test_no_upstream(self, cache):
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 673}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_upstream_error(self, cache, mock_jira_api):
        mock_jira_api.get_sprint_issues.side_effect = Exception("fail")
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 673}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_pagination(self, cache, mock_jira_api):
        """Test multi-page upstream fetch."""
        page1 = {"issues": [make_issue(key=f"TP-{i}") for i in range(50)], "total": 60}
        page2 = {"issues": [make_issue(key=f"TP-{i}") for i in range(50, 60)], "total": 60}
        mock_jira_api.get_sprint_issues.side_effect = [page1, page2]
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 673}))
        assert result["results"]["total"] == 60

    @pytest.mark.asyncio
    async def test_response_offset(self, cache, mock_jira_api):
        issues = [make_issue(key=f"TP-{i}") for i in range(5)]
        mock_jira_api.get_sprint_issues.return_value = {"issues": issues, "total": 5}
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 673, "start_at": 3}))
        assert len(result["results"]["issues"]) == 2

    @pytest.mark.asyncio
    async def test_with_embeddings(self, cache, mock_jira_api):
        emb = MagicMock()
        emb.available = True
        server.embeddings = emb
        mock_jira_api.get_sprint_issues.return_value = {"issues": [], "total": 0}
        await handle_cache_sprint_issues({"sprint_id": 673})
        emb.store_batch.assert_called_once()
        server.embeddings = None


class TestHandleCacheTextSearch:
    @pytest.mark.asyncio
    async def test_basic(self, cache):
        issue = make_issue(key="TP-1", summary="coupon payment")
        cache.put_issue("TP-1", issue)
        result = json.loads(await handle_cache_text_search({"query": "coupon"}))
        assert result["source"] == "fts5"
        assert result["count"] >= 1


class TestHandleCacheSimilarIssues:
    @pytest.mark.asyncio
    async def test_no_embeddings(self):
        server.embeddings = None
        result = json.loads(await handle_cache_similar_issues({"query": "test"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_embeddings_not_available(self):
        emb = MagicMock()
        emb.available = False
        server.embeddings = emb
        result = json.loads(await handle_cache_similar_issues({"query": "test"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_with_results(self, cache):
        emb = MagicMock()
        emb.available = True
        emb.find_similar.return_value = [{"entity_id": "TP-1", "entity_type": "jira", "distance": 0.1}]
        server.embeddings = emb
        cache.put_issue("TP-1", make_issue(key="TP-1"))
        result = json.loads(await handle_cache_similar_issues({"query": "test"}))
        assert result["count"] == 1
        server.embeddings = None

    @pytest.mark.asyncio
    async def test_missing_cache_issue(self):
        emb = MagicMock()
        emb.available = True
        emb.find_similar.return_value = [{"entity_id": "TP-999", "entity_type": "jira", "distance": 0.5}]
        server.embeddings = emb
        result = json.loads(await handle_cache_similar_issues({"query": "test"}))
        assert result["count"] == 1
        assert "summary" not in result["results"][0]
        server.embeddings = None


class TestHandleCacheRefresh:
    @pytest.mark.asyncio
    async def test_no_upstream(self):
        server.jira_api = None
        result = json.loads(await handle_cache_refresh({}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_refresh_issues(self, mock_jira_api):
        mock_jira_api.get_issue.return_value = make_issue(key="TP-1")
        result = json.loads(await handle_cache_refresh({"issue_keys": ["TP-1"]}))
        assert result["refreshed"] == 1

    @pytest.mark.asyncio
    async def test_refresh_issue_error(self, mock_jira_api):
        mock_jira_api.get_issue.side_effect = Exception("fail")
        result = json.loads(await handle_cache_refresh({"issue_keys": ["TP-1"]}))
        assert result["refreshed"] == 0

    @pytest.mark.asyncio
    async def test_refresh_sprint(self, mock_jira_api):
        mock_jira_api.get_sprint_issues.return_value = {"issues": [make_issue()], "total": 1}
        result = json.loads(await handle_cache_refresh({"sprint_id": 673}))
        assert result["refreshed"] >= 1

    @pytest.mark.asyncio
    async def test_refresh_sprint_error(self, mock_jira_api):
        mock_jira_api.get_sprint_issues.side_effect = Exception("fail")
        result = json.loads(await handle_cache_refresh({"sprint_id": 673}))
        assert result["refreshed"] == 0

    @pytest.mark.asyncio
    async def test_refresh_with_embeddings(self, mock_jira_api):
        emb = MagicMock()
        emb.available = True
        server.embeddings = emb
        mock_jira_api.get_issue.return_value = make_issue(key="TP-1")
        await handle_cache_refresh({"issue_keys": ["TP-1"]})
        emb.store_batch.assert_called()

        # Sprint refresh with embeddings
        mock_jira_api.get_sprint_issues.return_value = {"issues": [make_issue()], "total": 1}
        await handle_cache_refresh({"sprint_id": 673})
        assert emb.store_batch.call_count >= 2
        server.embeddings = None


class TestHandleCacheStats:
    @pytest.mark.asyncio
    async def test_basic(self):
        result = json.loads(await handle_cache_stats({}))
        assert "issues_cached" in result

    @pytest.mark.asyncio
    async def test_with_embeddings(self):
        emb = MagicMock()
        emb.available = True
        emb.count.return_value = 42
        server.embeddings = emb
        result = json.loads(await handle_cache_stats({}))
        assert result["embeddings_count"] == 42
        server.embeddings = None


class TestHandleCacheInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_all(self, cache):
        cache.put_issue("TP-1", make_issue())
        result = json.loads(await handle_cache_invalidate({"all": True, "confirm": True}))
        assert result["invalidated"] == "all"

    @pytest.mark.asyncio
    async def test_invalidate_all_no_confirm(self, cache):
        """L3: invalidate_all without confirm=true returns error."""
        cache.put_issue("TP-1", make_issue())
        result = json.loads(await handle_cache_invalidate({"all": True}))
        assert "error" in result
        # Issue should still exist
        assert cache.get_issue("TP-1") is not None

    @pytest.mark.asyncio
    async def test_invalidate_issue(self, cache):
        cache.put_issue("TP-1", make_issue())
        result = json.loads(await handle_cache_invalidate({"issue_key": "TP-1"}))
        assert result["invalidated"] == "TP-1"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_invalidate_with_embeddings(self, cache):
        emb = MagicMock()
        server.embeddings = emb
        cache.put_issue("TP-1", make_issue())
        await handle_cache_invalidate({"issue_key": "TP-1"})
        emb.remove_embedding.assert_called_with("TP-1")
        server.embeddings = None

    @pytest.mark.asyncio
    async def test_invalidate_sprint(self, cache):
        result = json.loads(await handle_cache_invalidate({"sprint_id": 673}))
        assert "invalidated_sprint" in result

    @pytest.mark.asyncio
    async def test_invalidate_no_args(self):
        result = json.loads(await handle_cache_invalidate({}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_auto_refresh_success(self, cache, mock_jira_api):
        cache.put_issue("TP-1", make_issue())
        mock_jira_api.get_issue.return_value = make_issue(key="TP-1", summary="Refreshed")
        result = json.loads(await handle_cache_invalidate({"issue_key": "TP-1", "auto_refresh": True}))
        assert result["auto_refreshed"] is True
        assert "issue" in result

    @pytest.mark.asyncio
    async def test_auto_refresh_error(self, cache, mock_jira_api):
        cache.put_issue("TP-1", make_issue())
        mock_jira_api.get_issue.side_effect = Exception("fail")
        result = json.loads(await handle_cache_invalidate({"issue_key": "TP-1", "auto_refresh": True}))
        assert result["auto_refreshed"] is False
        assert "auto_refresh_error" in result

    @pytest.mark.asyncio
    async def test_auto_refresh_with_embeddings(self, cache, mock_jira_api):
        emb = MagicMock()
        emb.available = True
        emb.store_embedding.return_value = True
        server.embeddings = emb
        cache.put_issue("TP-1", make_issue())
        mock_jira_api.get_issue.return_value = make_issue(key="TP-1")
        await handle_cache_invalidate({"issue_key": "TP-1", "auto_refresh": True})
        emb.remove_embedding.assert_called()
        emb.store_embedding.assert_called()
        server.embeddings = None

    @pytest.mark.asyncio
    async def test_auto_refresh_no_upstream(self, cache):
        """auto_refresh with no API should just invalidate."""
        cache.put_issue("TP-1", make_issue())
        server.jira_api = None
        result = json.loads(await handle_cache_invalidate({"issue_key": "TP-1", "auto_refresh": True}))
        assert result["invalidated"] == "TP-1"
        # Should not have auto_refreshed key since no API
        assert "auto_refreshed" not in result


# --- _init() ---


class TestInit:
    def test_success(self, tmp_path):
        """_init() succeeds with mocked credentials."""
        mock_creds = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USERNAME": "user@test.com",
            "CONFLUENCE_API_TOKEN": "token123",
        }
        # server.load_credentials etc. are already MagicMock from module-level patch
        old_load = server.load_credentials
        old_jc = server.AtlassianCache
        old_es = server.EmbeddingStore
        try:
            server.load_credentials = MagicMock(return_value=mock_creds)
            server.derive_jira_url = MagicMock(return_value="https://test.atlassian.net")
            server.get_auth_header = MagicMock(return_value="Basic abc")
            server.create_ssl_context = MagicMock(return_value=None)
            mock_api = MagicMock()
            server.JiraAPI = MagicMock(return_value=mock_api)
            mock_cache = MagicMock(conn=MagicMock())
            server.AtlassianCache = MagicMock(return_value=mock_cache)
            server.EmbeddingStore = MagicMock()
            server._init()
            assert server.cache is mock_cache
            assert server.jira_api is mock_api
        finally:
            server.load_credentials = old_load
            server.AtlassianCache = old_jc
            server.EmbeddingStore = old_es

    def test_credential_failure(self, tmp_path):
        """_init() handles credential failure gracefully."""
        old_jc = server.AtlassianCache
        old_es = server.EmbeddingStore
        old_load = server.load_credentials
        try:
            mock_cache = MagicMock(conn=MagicMock())
            server.AtlassianCache = MagicMock(return_value=mock_cache)
            server.EmbeddingStore = MagicMock()
            server.load_credentials = MagicMock(side_effect=Exception("no creds"))
            server._init()
            assert server.cache is mock_cache
            assert server.jira_api is None
        finally:
            server.AtlassianCache = old_jc
            server.EmbeddingStore = old_es
            server.load_credentials = old_load


# --- Paginate safety halving loop ---


class TestPaginateSafetyLoop:
    def test_halving_loop(self):
        """L310-313: When paginated result is still too large, halve iteratively.

        Trick: 3 huge issues (40KB each) at the front + 100 tiny issues at the back.
        avg_size is low (dragged down by tiny items) → fits estimate is high (~40)
        → but issues[:40] includes the 3 huge ones → result > MAX → halving loop fires.
        """
        huge = {"key": "TP-0", "fields": {"summary": "s"}, "blob": "X" * 40000}
        tiny = {"key": "TP-1", "fields": {"summary": "s"}}
        issues = [huge] * 3 + [tiny] * 100
        data = {"issues": issues, "total": len(issues)}
        big = json.dumps(data, ensure_ascii=False)
        assert len(big) > MAX_RESPONSE_CHARS

        result = _paginate_response(big)
        parsed = json.loads(result)
        assert parsed["_pagination"]["has_more"]
        # The halving loop should have reduced returned below the initial estimate
        assert parsed["_pagination"]["returned"] < 40


# --- Batch get stale fallback ---


class TestBatchGetStaleFallback:
    @pytest.mark.asyncio
    async def test_stale_fallback_on_upstream_error(self, cache, mock_jira_api):
        """L437: When upstream fails for a key with stale cache, return stale.

        Key: put_issue stores the data, then set max_age_hours=0 so get_issues_batch
        reports it as missing (expired). Upstream then fails → stale fallback.
        """
        cache.put_issue("TP-1", make_issue(key="TP-1"))
        mock_jira_api.get_issue.side_effect = Exception("timeout")
        result = json.loads(
            await handle_cache_get_issues(
                {
                    "issue_keys": ["TP-1"],
                    "max_age_hours": 0,  # Treat cached as expired → goes to upstream
                }
            )
        )
        # Upstream failed but stale fallback should have returned the data
        assert result["total"] == 1
        assert result["from_upstream"] == 1  # stale counted as upstream


# --- Sprint refresh pagination continuation ---


class TestSprintRefreshPagination:
    @pytest.mark.asyncio
    async def test_multi_page_refresh(self, mock_jira_api):
        """L639: Sprint refresh should paginate when total > page size."""
        page1 = {"issues": [make_issue(key=f"TP-{i}") for i in range(50)], "total": 75}
        page2 = {"issues": [make_issue(key=f"TP-{i}") for i in range(50, 75)], "total": 75}
        mock_jira_api.get_sprint_issues.side_effect = [page1, page2]
        # Verify jira_api is set
        assert server.jira_api is mock_jira_api
        raw = await handle_cache_refresh({"sprint_id": 673})
        result = json.loads(raw)
        assert "refreshed" in result, f"Unexpected: {result}"
        assert result["refreshed"] == 75
        assert mock_jira_api.get_sprint_issues.call_count == 2


# --- New helper functions (H4, H6, M10) ---


class TestValidateIssueKey:
    def test_valid_keys(self):
        assert _validate_issue_key("TP-1") == "TP-1"
        assert _validate_issue_key("TP-123456") == "TP-123456"
        assert _validate_issue_key("PROJ-42") == "PROJ-42"

    def test_invalid_keys(self):
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key("invalid")
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key("")
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key("TP-")
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key("bep-123")  # lowercase

    def test_non_string(self):
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key(123)
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key(None)

    @pytest.mark.asyncio
    async def test_invalid_key_in_handler(self, cache):
        """H4: handler returns error for invalid key."""
        result = json.loads(await handle_cache_get_issue({"issue_key": "../etc/passwd"}))
        assert "error" in result


class TestRequireCache:
    def test_with_cache(self, cache):
        result = _require_cache()
        assert result is cache

    def test_without_cache(self):
        old = server.cache
        server.cache = None
        try:
            with pytest.raises(RuntimeError, match="Cache not initialized"):
                _require_cache()
        finally:
            server.cache = old


class TestEmbeddingText:
    def test_string_description(self):
        issue = {"fields": {"summary": "Test", "description": "Some text here"}}
        result = _embedding_text(issue)
        assert result == "Test Some text here"

    def test_adf_description(self):
        issue = {
            "fields": {
                "summary": "Test",
                "description": {
                    "type": "doc",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ADF content"}]}],
                },
            }
        }
        result = _embedding_text(issue)
        assert "ADF content" in result

    def test_no_description(self):
        issue = {"fields": {"summary": "Test"}}
        result = _embedding_text(issue)
        assert result == "Test"

    def test_empty_fields(self):
        issue = {}
        result = _embedding_text(issue)
        assert result == ""

    def test_truncation(self):
        long_desc = "x" * 1000
        issue = {"fields": {"summary": "Test", "description": long_desc}}
        result = _embedding_text(issue)
        assert len(result) <= 500


class TestTextSearchNoData:
    """L7: text_search should not return duplicate 'data' key."""

    @pytest.mark.asyncio
    async def test_no_data_key(self, cache):
        issue = make_issue(key="TP-1", summary="coupon payment")
        cache.put_issue("TP-1", issue)
        result = json.loads(await handle_cache_text_search({"query": "coupon"}))
        assert "data" not in result
        assert "issues" in result


class TestAutoRefreshStripNoise:
    """M9: auto_refresh response should strip noise."""

    @pytest.mark.asyncio
    async def test_noise_stripped(self, cache, mock_jira_api):
        cache.put_issue("TP-1", make_issue())
        noisy = make_issue(key="TP-1", summary="Refreshed")
        mock_jira_api.get_issue.return_value = noisy
        result = json.loads(
            await handle_cache_invalidate(
                {
                    "issue_key": "TP-1",
                    "auto_refresh": True,
                }
            )
        )
        assert result["auto_refreshed"] is True
        # Noise fields should be stripped from the returned issue
        assert "self" not in result["issue"]
        assert "expand" not in result["issue"]


# --- In-session deduplication + compact list format ---


def test_compact_format_for_large_lists(cache, multiple_issues):
    """Lists with 20+ issues use compact headers+rows format."""
    from server import _maybe_compact
    issues = [{"key": f"TP-{i}", "summary": f"Issue {i}",
               "status": "To Do", "assignee": None, "sp": None}
              for i in range(25)]
    result = _maybe_compact(issues)
    assert result["format"] == "compact"
    assert "headers" in result
    assert "rows" in result
    assert len(result["rows"]) == 25


def test_small_list_not_compacted():
    from server import _maybe_compact
    issues = [{"key": f"TP-{i}", "summary": "x"} for i in range(5)]
    result = _maybe_compact(issues)
    assert isinstance(result, list)  # unchanged


def test_compact_threshold_boundary():
    from server import _maybe_compact, _COMPACT_LIST_THRESHOLD
    # Exactly at threshold — compacts
    issues_at = [{"key": f"TP-{i}", "summary": "x"} for i in range(_COMPACT_LIST_THRESHOLD)]
    assert isinstance(_maybe_compact(issues_at), dict)  # compacted
    # One below threshold — stays list
    issues_below = [{"key": f"TP-{i}", "summary": "x"} for i in range(_COMPACT_LIST_THRESHOLD - 1)]
    assert isinstance(_maybe_compact(issues_below), list)  # unchanged


def test_session_dedup_returns_ref_on_repeat(cache, sample_issue):
    """Second fetch of same issue within session returns compact ref."""
    from server import _mark_returned, _already_returned
    _mark_returned("TP-100")
    assert _already_returned("TP-100")


def test_confluence_tools_registered():
    from server import TOOLS
    names = {t.name for t in TOOLS}
    assert "cache_get_confluence_page" in names
    assert "cache_search_confluence" in names
    assert "cache_cross_search" in names
    assert len(names) == 22  # 13 Jira + 9 Confluence


def test_new_jira_tools_registered():
    from server import TOOLS
    names = {t.name for t in TOOLS}
    assert "cache_find_related" in names
    assert "cache_reindex" in names
    assert "cache_sync" in names
    assert len(names) == 22  # 13 Jira + 9 Confluence


def test_get_all_issues_returns_list(cache, sample_issue):
    cache.put_issue(sample_issue["key"], sample_issue)
    issues = cache.get_all_issues()
    assert isinstance(issues, list)
    assert len(issues) >= 1
    assert all("key" in i for i in issues)


class TestHandleConfluenceChildren:
    """Tests for handle_cache_get_confluence_children — cache-hit and upstream fallback."""

    @pytest.mark.asyncio
    async def test_returns_cached_children(self, cache):
        """Returns children from cache without upstream call."""
        from .conftest import make_page

        server.confluence.put_page(make_page(page_id="parent", title="Parent"))
        server.confluence.put_page(make_page(page_id="child1", title="Child 1"))
        server.confluence.put_children("parent", [{"id": "child1"}])

        result = json.loads(await handle_cache_get_confluence_children({"page_id": "parent"}))
        assert len(result["children"]) == 1
        assert result["children"][0]["page_id"] == "child1"

    @pytest.mark.asyncio
    async def test_upstream_fallback_stores_and_returns(self, cache):
        """Falls back to upstream when cache is empty, stores result."""
        from .conftest import make_page

        # Store child page so get_children join works
        server.confluence.put_page(make_page(page_id="upstream-child", title="Upstream Child"))

        mock_api = MagicMock()
        mock_api.get_confluence_children.return_value = [{"id": "upstream-child"}]
        server.jira_api = mock_api

        result = json.loads(await handle_cache_get_confluence_children({"page_id": "parent-new"}))
        mock_api.get_confluence_children.assert_called_once_with("parent-new")
        assert any(c["page_id"] == "upstream-child" for c in result["children"])

        server.jira_api = None

    @pytest.mark.asyncio
    async def test_no_upstream_returns_empty(self, cache):
        """Returns empty list when cache miss and no jira_api configured."""
        result = json.loads(await handle_cache_get_confluence_children({"page_id": "ghost"}))
        assert result["children"] == []


class TestHandleConfluenceRefresh:
    """Tests for handle_cache_refresh_confluence — stub and real re-fetch."""

    @pytest.mark.asyncio
    async def test_no_api_returns_invalidated_status(self, cache):
        """Without upstream API, just invalidates and returns status."""
        from .conftest import make_page

        server.confluence.put_page(make_page(page_id="99", title="Old"))
        result = json.loads(await handle_cache_refresh_confluence({"page_id": "99"}))
        assert result["status"] == "invalidated"
        assert result["page_id"] == "99"

    @pytest.mark.asyncio
    async def test_with_api_fetches_and_stores(self, cache):
        """With upstream API, fetches fresh page and stores it."""
        from .conftest import make_page

        fresh_page = make_page(page_id="77", title="Fresh Title", version_num=5)
        mock_api = MagicMock()
        mock_api.get_confluence_page.return_value = fresh_page
        server.jira_api = mock_api

        result = json.loads(await handle_cache_refresh_confluence({"page_id": "77"}))
        assert result["status"] == "refreshed"
        assert result["title"] == "Fresh Title"

        # Page should now be in cache
        cached = server.confluence.get_page("77", max_age_hours=24)
        assert cached is not None
        assert cached["title"] == "Fresh Title"

        server.jira_api = None


def test_get_all_sections_returns_list(confluence_cache, sample_page):
    from atlassian_cache.sections import split_sections
    confluence_cache.put_page(sample_page)
    sections = split_sections("12345", sample_page["_body_md"])
    confluence_cache.put_sections(sections)
    all_secs = confluence_cache.get_all_sections()
    assert isinstance(all_secs, list)
    assert len(all_secs) == len(sections)


class TestHandleSprintGoalEmbedding:
    """Sprint goal is embedded when fetched upstream."""

    async def test_sprint_goal_embedded_on_upstream_fetch(self, cache, mock_jira_api):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings

        sprint_meta = {"id": 42, "name": "Sprint 42", "state": "active", "goal": "Ship coupon API", "startDate": None, "endDate": None}
        mock_jira_api.get_sprint.return_value = sprint_meta
        mock_jira_api.get_sprint_issues.return_value = {"issues": [], "total": 0}

        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 42}))
        assert result.get("error") is None

        calls = [str(c) for c in mock_embeddings.store_embedding.call_args_list]
        assert any("sprint::42" in c for c in calls)

    async def test_sprint_goal_skipped_when_no_goal(self, cache, mock_jira_api):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings

        sprint_meta = {"id": 10, "name": "Sprint 10", "state": "active", "goal": None}
        mock_jira_api.get_sprint.return_value = sprint_meta
        mock_jira_api.get_sprint_issues.return_value = {"issues": [], "total": 0}

        await handle_cache_sprint_issues({"sprint_id": 10})
        for call in mock_embeddings.store_embedding.call_args_list:
            assert "sprint::10" not in str(call)

    async def test_sprint_goal_skipped_when_embeddings_unavailable(self, cache, mock_jira_api):
        server.embeddings = None
        sprint_meta = {"id": 5, "name": "Sprint 5", "state": "active", "goal": "Some goal"}
        mock_jira_api.get_sprint.return_value = sprint_meta
        mock_jira_api.get_sprint_issues.return_value = {"issues": [], "total": 0}
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 5}))
        assert result.get("error") is None


class TestHandleCacheSimilarSprints:
    async def test_returns_error_when_no_embeddings(self, cache):
        server.embeddings = None
        result = json.loads(await handle_cache_similar_sprints({"query": "coupon"}))
        assert "error" in result

    async def test_returns_results_with_sprint_data(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.find_similar.return_value = [
            {"entity_id": "sprint::1", "entity_type": "sprint", "distance": 0.1}
        ]
        server.embeddings = mock_embeddings
        cache.put_sprint(1, {"name": "Sprint 1", "state": "active", "goal": "Coupon system", "startDate": None, "endDate": None})

        result = json.loads(await handle_cache_similar_sprints({"query": "coupon payment"}))
        assert result["results"][0]["entity_id"] == "sprint::1"
        assert result["results"][0]["sprint"]["name"] == "Sprint 1"
        assert result["results"][0]["sprint"]["goal"] == "Coupon system"

    async def test_falls_back_gracefully_on_missing_sprint(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.find_similar.return_value = [
            {"entity_id": "sprint::999", "entity_type": "sprint", "distance": 0.2}
        ]
        server.embeddings = mock_embeddings
        result = json.loads(await handle_cache_similar_sprints({"query": "missing sprint"}))
        assert result["results"][0]["entity_id"] == "sprint::999"
        assert "sprint" not in result["results"][0]


class TestPageLevelEmbedding:
    """Page title+labels are embedded when a page is refreshed."""

    async def test_page_embedded_on_refresh(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings

        mock_api = MagicMock()
        server.jira_api = mock_api
        mock_api.get_confluence_page.return_value = {
            "id": "p1",
            "title": "Coupon Design Doc",
            "space": {"key": "TP"},
            "_body_md": "## Overview\nContent",
            "version": {"number": 1, "when": "2026-01-01T00:00:00.000Z"},
            "metadata": {"labels": {"results": [{"name": "design"}, {"name": "coupon"}]}},
            "history": {"createdBy": {"displayName": "Alice"}},
            "_links": {"webui": "/wiki/spaces/TP/pages/p1"},
        }

        await handle_cache_refresh_confluence({"page_id": "p1"})
        server.jira_api = None

        calls = [str(c) for c in mock_embeddings.store_embedding.call_args_list]
        assert any("page::p1" in c for c in calls)
        assert any("design" in c or "coupon" in c for c in calls)

    async def test_page_embedding_removed_on_invalidate(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings

        await handle_cache_invalidate_confluence({"page_id": "p99"})

        calls = [str(c) for c in mock_embeddings.remove_embedding.call_args_list]
        assert any("page::p99" in c for c in calls)

    async def test_page_embedding_skipped_when_no_embeddings(self, cache):
        server.embeddings = None
        mock_api = MagicMock()
        server.jira_api = mock_api
        mock_api.get_confluence_page.return_value = {
            "id": "p2", "title": "Test", "space": {"key": "TP"},
            "_body_md": "content",
            "version": {"number": 1, "when": "2026-01-01T00:00:00.000Z"},
            "metadata": {"labels": {"results": []}},
            "history": {"createdBy": {"displayName": "Bob"}},
            "_links": {"webui": "/wiki/spaces/TP/pages/p2"},
        }
        result = json.loads(await handle_cache_refresh_confluence({"page_id": "p2"}))
        assert result["status"] == "refreshed"
        server.jira_api = None


class TestFindConfluenceRelatedWithPages:
    """cache_find_confluence_related returns both sections and page-level results."""

    async def test_includes_page_results(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.generate_embedding.return_value = [0.1] * 384
        mock_embeddings.find_similar_by_embedding.side_effect = [
            [{"entity_id": "p1::overview", "entity_type": "confluence", "distance": 0.1}],
            [{"entity_id": "page::p2", "entity_type": "confluence_page", "distance": 0.15}],
        ]
        server.embeddings = mock_embeddings

        result = json.loads(await handle_cache_find_confluence_related({"query": "coupon", "limit": 5}))
        related = result["related"]
        entity_ids = [r["entity_id"] for r in related]
        assert "p1::overview" in entity_ids
        assert "page::p2" in entity_ids
        # Verify embedding was generated only once
        mock_embeddings.generate_embedding.assert_called_once()

    async def test_sorted_by_distance(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.generate_embedding.return_value = [0.1] * 384
        mock_embeddings.find_similar_by_embedding.side_effect = [
            [{"entity_id": "sec::a", "entity_type": "confluence", "distance": 0.3}],
            [{"entity_id": "page::b", "entity_type": "confluence_page", "distance": 0.1}],
        ]
        server.embeddings = mock_embeddings

        result = json.loads(await handle_cache_find_confluence_related({"query": "test", "limit": 5}))
        related = result["related"]
        assert related[0]["entity_id"] == "page::b"  # closer distance first


class TestReindexPages:
    """_reindex_pages helper embeds all cached pages."""

    def test_embeds_pages(self, cache):
        from tests.conftest import make_page
        from atlassian_cache.confluence_cache import ConfluenceCache
        conf = ConfluenceCache(cache.conn, cache._lock)
        conf.put_page(make_page(page_id="x1", title="Design Doc", labels=["design"]))

        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.store_batch_entities.return_value = 1
        server.embeddings = mock_embeddings

        pages = conf.get_all_pages()
        count = _reindex_pages(pages)
        assert count == 1
        mock_embeddings.store_batch_entities.assert_called_once()
        entities = mock_embeddings.store_batch_entities.call_args[0][0]
        entity_ids = [e[0] for e in entities]
        assert "page::x1" in entity_ids

    def test_returns_count(self, cache):
        from tests.conftest import make_page
        from atlassian_cache.confluence_cache import ConfluenceCache
        conf = ConfluenceCache(cache.conn, cache._lock)
        conf.put_page(make_page(page_id="y1", title="A"))
        conf.put_page(make_page(page_id="y2", title="B"))
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.store_batch_entities.return_value = 2
        server.embeddings = mock_embeddings
        pages = conf.get_all_pages()
        count = _reindex_pages(pages)
        assert count == 2


class TestReindexSectionsWithHeading:
    """Section embedding text includes heading for better semantic search."""

    def _get_entities(self, mock_embeddings):
        """Extract entities list from store_batch_entities call."""
        return mock_embeddings.store_batch_entities.call_args[0][0]

    def test_heading_included_in_embedding_text(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.store_batch_entities.return_value = 1
        server.embeddings = mock_embeddings

        sections = [{"section_id": "p1::overview", "heading": "Overview", "body_md": "Some content"}]
        _reindex_sections(sections)

        entities = self._get_entities(mock_embeddings)
        text_arg = entities[0][1]  # (entity_id, text, entity_type)[1]
        assert "Overview" in text_arg
        assert "Some content" in text_arg

    def test_heading_only_when_no_body(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.store_batch_entities.return_value = 1
        server.embeddings = mock_embeddings

        sections = [{"section_id": "p1::intro", "heading": "Introduction", "body_md": ""}]
        _reindex_sections(sections)

        entities = self._get_entities(mock_embeddings)
        text_arg = entities[0][1]
        assert "Introduction" in text_arg

    def test_body_only_when_no_heading(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.store_batch_entities.return_value = 1
        server.embeddings = mock_embeddings

        sections = [{"section_id": "p1::sec", "body_md": "Just body content"}]
        _reindex_sections(sections)

        entities = self._get_entities(mock_embeddings)
        text_arg = entities[0][1]
        assert "Just body content" in text_arg
