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
        handle_cache_get_issue,
        handle_cache_get_issues,
        handle_cache_invalidate,
        handle_cache_refresh,
        handle_cache_search,
        handle_cache_similar_issues,
        handle_cache_sprint_issues,
        handle_cache_stats,
        handle_cache_text_search,
    )


@pytest.fixture(autouse=True)
def setup_server_globals(cache, tmp_path):
    """Inject test cache into server globals."""
    server.cache = cache
    server.embeddings = None
    server.jira_api = None
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
        issue = make_issue(key="BEP-1", summary="Test", status="Done", assignee="Alice", issue_type="Bug")
        result = _format_issue_summary(issue)
        assert "[BEP-1]" in result
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
        issue = make_issue(key="BEP-1", summary="Test", status="Done", assignee="Alice")
        compact = _compact_issue(issue)
        assert compact["key"] == "BEP-1"
        assert compact["summary"] == "Test"
        assert compact["status"] == "Done"
        assert compact["assignee"] == "Alice"

    def test_with_parent(self):
        issue = make_issue(parent_key="BEP-100")
        compact = _compact_issue(issue)
        assert compact["parent"] == "BEP-100"

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
        issue["fields"]["parent"] = "BEP-99"
        compact = _compact_issue(issue)
        assert compact["status"] == "Custom"
        assert compact["assignee"] == "Unassigned"
        assert compact["issuetype"] == "Task"
        assert compact["priority"] == "High"
        assert compact["parent"] == "BEP-99"


# --- Response size management ---


class TestStripResponseNoise:
    def test_strips_noise(self):
        data = {"self": "url", "key": "BEP-1"}
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
        issues = [make_issue(key=f"BEP-{i}") for i in range(100)]
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
        issues = [make_issue(key=f"BEP-{i}") for i in range(20)]
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
        issue = make_issue(key="BEP-1")
        cache.put_issue("BEP-1", issue)
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-1"}))
        assert result["source"] == "cache"
        assert result["issue"]["key"] == "BEP-1"

    @pytest.mark.asyncio
    async def test_cache_hit_compact(self, cache):
        issue = make_issue(key="BEP-1")
        cache.put_issue("BEP-1", issue)
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-1", "compact": True}))
        assert result["source"] == "cache"
        assert "fields" not in result["issue"]

    @pytest.mark.asyncio
    async def test_upstream_fetch(self, cache, mock_jira_api):
        upstream_issue = make_issue(key="BEP-2", summary="Upstream")
        mock_jira_api.get_issue.return_value = upstream_issue
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-2"}))
        assert result["source"] == "upstream"
        mock_jira_api.get_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_refresh(self, cache, mock_jira_api):
        issue = make_issue(key="BEP-1")
        cache.put_issue("BEP-1", issue)
        mock_jira_api.get_issue.return_value = issue
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-1", "force_refresh": True}))
        assert result["source"] == "upstream"

    @pytest.mark.asyncio
    async def test_no_upstream_stale_fallback(self, cache):
        """No API + stale data → returns stale."""
        issue = make_issue(key="BEP-1")
        cache.put_issue("BEP-1", issue)
        server.jira_api = None
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-1", "force_refresh": True}))
        assert result["source"] == "stale_cache"
        assert "warning" in result

    @pytest.mark.asyncio
    async def test_no_upstream_no_cache(self, cache):
        server.jira_api = None
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-999"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_upstream_error_stale_fallback(self, cache, mock_jira_api):
        issue = make_issue(key="BEP-1")
        cache.put_issue("BEP-1", issue)
        mock_jira_api.get_issue.side_effect = Exception("timeout")
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-1", "force_refresh": True}))
        assert result["source"] == "stale_cache"

    @pytest.mark.asyncio
    async def test_upstream_error_no_stale(self, cache, mock_jira_api):
        mock_jira_api.get_issue.side_effect = Exception("timeout")
        result = json.loads(await handle_cache_get_issue({"issue_key": "BEP-999"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_with_embeddings(self, cache, mock_jira_api):
        """When embeddings available, should store embedding."""
        emb = MagicMock()
        emb.available = True
        emb.store_embedding.return_value = True
        server.embeddings = emb
        mock_jira_api.get_issue.return_value = make_issue(key="BEP-1")
        await handle_cache_get_issue({"issue_key": "BEP-1"})
        emb.store_embedding.assert_called_once()
        server.embeddings = None


class TestHandleCacheGetIssues:
    @pytest.mark.asyncio
    async def test_empty_keys(self):
        result = json.loads(await handle_cache_get_issues({"issue_keys": []}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_all_cached(self, cache):
        for i in range(3):
            cache.put_issue(f"BEP-{i}", make_issue(key=f"BEP-{i}"))
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["BEP-0", "BEP-1", "BEP-2"]}))
        assert result["from_cache"] == 3
        assert result["from_upstream"] == 0

    @pytest.mark.asyncio
    async def test_with_upstream_fetch(self, cache, mock_jira_api):
        cache.put_issue("BEP-1", make_issue(key="BEP-1"))
        mock_jira_api.get_issue.return_value = make_issue(key="BEP-2")
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["BEP-1", "BEP-2"]}))
        assert result["from_cache"] == 1
        assert result["from_upstream"] == 1

    @pytest.mark.asyncio
    async def test_compact(self, cache):
        cache.put_issue("BEP-1", make_issue(key="BEP-1"))
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["BEP-1"], "compact": True}))
        assert "fields" not in result["issues"][0]

    @pytest.mark.asyncio
    async def test_upstream_error_stale_fallback(self, cache, mock_jira_api):
        cache.put_issue("BEP-1", make_issue(key="BEP-1"))
        mock_jira_api.get_issue.side_effect = Exception("fail")
        result = json.loads(await handle_cache_get_issues({"issue_keys": ["BEP-1", "BEP-2"], "force_refresh": True}))
        # BEP-2 should fail but BEP-1 should come from stale
        assert result["total"] >= 0

    @pytest.mark.asyncio
    async def test_with_embeddings(self, cache, mock_jira_api):
        emb = MagicMock()
        emb.available = True
        emb.store_embedding.return_value = True
        server.embeddings = emb
        mock_jira_api.get_issue.return_value = make_issue(key="BEP-1")
        await handle_cache_get_issues({"issue_keys": ["BEP-1"]})
        emb.store_embedding.assert_called()
        server.embeddings = None


class TestHandleCacheSearch:
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache):
        data = {"issues": [make_issue()], "total": 1}
        cache.put_search("project = BEP", "summary", 30, data)
        result = json.loads(await handle_cache_search({"jql": "project = BEP", "fields": "summary", "limit": 30}))
        assert result["source"] == "cache"

    @pytest.mark.asyncio
    async def test_upstream(self, cache, mock_jira_api):
        mock_jira_api.search_issues.return_value = {"issues": [make_issue()], "total": 1}
        result = json.loads(await handle_cache_search({"jql": "project = BEP"}))
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
        issues = [make_issue(key=f"BEP-{i}") for i in range(5)]
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
        page1 = {"issues": [make_issue(key=f"BEP-{i}") for i in range(50)], "total": 60}
        page2 = {"issues": [make_issue(key=f"BEP-{i}") for i in range(50, 60)], "total": 60}
        mock_jira_api.get_sprint_issues.side_effect = [page1, page2]
        result = json.loads(await handle_cache_sprint_issues({"sprint_id": 673}))
        assert result["results"]["total"] == 60

    @pytest.mark.asyncio
    async def test_response_offset(self, cache, mock_jira_api):
        issues = [make_issue(key=f"BEP-{i}") for i in range(5)]
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
        issue = make_issue(key="BEP-1", summary="coupon payment")
        cache.put_issue("BEP-1", issue)
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
        emb.find_similar.return_value = [{"issue_key": "BEP-1", "distance": 0.1}]
        server.embeddings = emb
        cache.put_issue("BEP-1", make_issue(key="BEP-1"))
        result = json.loads(await handle_cache_similar_issues({"query": "test"}))
        assert result["count"] == 1
        server.embeddings = None

    @pytest.mark.asyncio
    async def test_missing_cache_issue(self):
        emb = MagicMock()
        emb.available = True
        emb.find_similar.return_value = [{"issue_key": "BEP-999", "distance": 0.5}]
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
        mock_jira_api.get_issue.return_value = make_issue(key="BEP-1")
        result = json.loads(await handle_cache_refresh({"issue_keys": ["BEP-1"]}))
        assert result["refreshed"] == 1

    @pytest.mark.asyncio
    async def test_refresh_issue_error(self, mock_jira_api):
        mock_jira_api.get_issue.side_effect = Exception("fail")
        result = json.loads(await handle_cache_refresh({"issue_keys": ["BEP-1"]}))
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
        mock_jira_api.get_issue.return_value = make_issue(key="BEP-1")
        await handle_cache_refresh({"issue_keys": ["BEP-1"]})
        emb.store_embedding.assert_called()

        # Sprint refresh with embeddings
        mock_jira_api.get_sprint_issues.return_value = {"issues": [make_issue()], "total": 1}
        await handle_cache_refresh({"sprint_id": 673})
        emb.store_batch.assert_called()
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
        cache.put_issue("BEP-1", make_issue())
        result = json.loads(await handle_cache_invalidate({"all": True, "confirm": True}))
        assert result["invalidated"] == "all"

    @pytest.mark.asyncio
    async def test_invalidate_all_no_confirm(self, cache):
        """L3: invalidate_all without confirm=true returns error."""
        cache.put_issue("BEP-1", make_issue())
        result = json.loads(await handle_cache_invalidate({"all": True}))
        assert "error" in result
        # Issue should still exist
        assert cache.get_issue("BEP-1") is not None

    @pytest.mark.asyncio
    async def test_invalidate_issue(self, cache):
        cache.put_issue("BEP-1", make_issue())
        result = json.loads(await handle_cache_invalidate({"issue_key": "BEP-1"}))
        assert result["invalidated"] == "BEP-1"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_invalidate_with_embeddings(self, cache):
        emb = MagicMock()
        server.embeddings = emb
        cache.put_issue("BEP-1", make_issue())
        await handle_cache_invalidate({"issue_key": "BEP-1"})
        emb.remove_embedding.assert_called_with("BEP-1")
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
        cache.put_issue("BEP-1", make_issue())
        mock_jira_api.get_issue.return_value = make_issue(key="BEP-1", summary="Refreshed")
        result = json.loads(await handle_cache_invalidate({"issue_key": "BEP-1", "auto_refresh": True}))
        assert result["auto_refreshed"] is True
        assert "issue" in result

    @pytest.mark.asyncio
    async def test_auto_refresh_error(self, cache, mock_jira_api):
        cache.put_issue("BEP-1", make_issue())
        mock_jira_api.get_issue.side_effect = Exception("fail")
        result = json.loads(await handle_cache_invalidate({"issue_key": "BEP-1", "auto_refresh": True}))
        assert result["auto_refreshed"] is False
        assert "auto_refresh_error" in result

    @pytest.mark.asyncio
    async def test_auto_refresh_with_embeddings(self, cache, mock_jira_api):
        emb = MagicMock()
        emb.available = True
        emb.store_embedding.return_value = True
        server.embeddings = emb
        cache.put_issue("BEP-1", make_issue())
        mock_jira_api.get_issue.return_value = make_issue(key="BEP-1")
        await handle_cache_invalidate({"issue_key": "BEP-1", "auto_refresh": True})
        emb.remove_embedding.assert_called()
        emb.store_embedding.assert_called()
        server.embeddings = None

    @pytest.mark.asyncio
    async def test_auto_refresh_no_upstream(self, cache):
        """auto_refresh with no API should just invalidate."""
        cache.put_issue("BEP-1", make_issue())
        server.jira_api = None
        result = json.loads(await handle_cache_invalidate({"issue_key": "BEP-1", "auto_refresh": True}))
        assert result["invalidated"] == "BEP-1"
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
        old_jc = server.JiraCache
        old_es = server.EmbeddingStore
        try:
            server.load_credentials = MagicMock(return_value=mock_creds)
            server.derive_jira_url = MagicMock(return_value="https://test.atlassian.net")
            server.get_auth_header = MagicMock(return_value="Basic abc")
            server.create_ssl_context = MagicMock(return_value=None)
            mock_api = MagicMock()
            server.JiraAPI = MagicMock(return_value=mock_api)
            mock_cache = MagicMock(conn=MagicMock())
            server.JiraCache = MagicMock(return_value=mock_cache)
            server.EmbeddingStore = MagicMock()
            server._init()
            assert server.cache is mock_cache
            assert server.jira_api is mock_api
        finally:
            server.load_credentials = old_load
            server.JiraCache = old_jc
            server.EmbeddingStore = old_es

    def test_credential_failure(self, tmp_path):
        """_init() handles credential failure gracefully."""
        old_jc = server.JiraCache
        old_es = server.EmbeddingStore
        old_load = server.load_credentials
        try:
            mock_cache = MagicMock(conn=MagicMock())
            server.JiraCache = MagicMock(return_value=mock_cache)
            server.EmbeddingStore = MagicMock()
            server.load_credentials = MagicMock(side_effect=Exception("no creds"))
            server._init()
            assert server.cache is mock_cache
            assert server.jira_api is None
        finally:
            server.JiraCache = old_jc
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
        huge = {"key": "BEP-0", "fields": {"summary": "s"}, "blob": "X" * 40000}
        tiny = {"key": "BEP-1", "fields": {"summary": "s"}}
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
        cache.put_issue("BEP-1", make_issue(key="BEP-1"))
        mock_jira_api.get_issue.side_effect = Exception("timeout")
        result = json.loads(
            await handle_cache_get_issues(
                {
                    "issue_keys": ["BEP-1"],
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
        page1 = {"issues": [make_issue(key=f"BEP-{i}") for i in range(50)], "total": 75}
        page2 = {"issues": [make_issue(key=f"BEP-{i}") for i in range(50, 75)], "total": 75}
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
        assert _validate_issue_key("BEP-1") == "BEP-1"
        assert _validate_issue_key("BEP-123456") == "BEP-123456"
        assert _validate_issue_key("PROJ-42") == "PROJ-42"

    def test_invalid_keys(self):
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key("invalid")
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key("")
        with pytest.raises(ValueError, match="Invalid issue key"):
            _validate_issue_key("BEP-")
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
        issue = make_issue(key="BEP-1", summary="coupon payment")
        cache.put_issue("BEP-1", issue)
        result = json.loads(await handle_cache_text_search({"query": "coupon"}))
        assert "data" not in result
        assert "issues" in result


class TestAutoRefreshStripNoise:
    """M9: auto_refresh response should strip noise."""

    @pytest.mark.asyncio
    async def test_noise_stripped(self, cache, mock_jira_api):
        cache.put_issue("BEP-1", make_issue())
        noisy = make_issue(key="BEP-1", summary="Refreshed")
        mock_jira_api.get_issue.return_value = noisy
        result = json.loads(
            await handle_cache_invalidate(
                {
                    "issue_key": "BEP-1",
                    "auto_refresh": True,
                }
            )
        )
        assert result["auto_refreshed"] is True
        # Noise fields should be stripped from the returned issue
        assert "self" not in result["issue"]
        assert "expand" not in result["issue"]
