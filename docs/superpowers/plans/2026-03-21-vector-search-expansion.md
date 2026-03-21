# Vector Search Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand semantic vector search coverage to sprint goals, Confluence page titles, and improve section embeddings by including headings.

**Architecture:** Three independent changes to `server.py` and supporting modules: (1) embed sprint `goal` field when sprint issues are fetched, expose via new `cache_similar_sprints` tool; (2) embed Confluence page `title + labels` as a page-level entity separate from section-level entities; (3) include section `heading` in the text used for section embeddings, making section search more accurate.

**Tech Stack:** Python 3.11+, sqlite-vec (vec0 virtual table), sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384-dim), pytest-asyncio, MCP server (stdio)

---

## File Structure

```
mcp-servers/atlassian-cache/
├── server.py                          # main: new handler + edits to 5 handlers + TOOLS + HANDLERS
├── atlassian_cache/cache.py           # add get_all_sprints()
├── atlassian_cache/confluence_cache.py # add get_all_pages()
tests/
├── test_server.py                     # new tests: sprint similar, page embedding, section heading
├── test_cache.py                      # new: test get_all_sprints()
├── test_confluence_cache.py           # new: test get_all_pages()
scripts/lib/jira_api.py                # add get_sprint(sprint_id) method
```

**Entity types in embeddings table after this plan:**

| entity_type | entity_id format | text embedded |
|---|---|---|
| `"jira"` | `"BEP-123"` | `summary + description[:500]` |
| `"sprint"` | `"sprint::123"` | `"Sprint Name goal: Sprint Goal text"` |
| `"confluence"` | `"page_id::heading-slug"` | `"heading\nbody_md"` (Task 3 change) |
| `"confluence_page"` | `"page::page_id"` | `"title labels"` |

---

## Task 1: add `get_sprint()` to JiraAPI

**Files:**

- Modify: `scripts/lib/jira_api.py` (after `get_sprint_issues` method, around line 296)
- Test: Not separately tested — validated via integration in Task 2

- [ ] **Step 1: Add the method**

Add this method to `JiraAPI` class in `scripts/lib/jira_api.py` after `get_sprint_issues`:

```python
def get_sprint(self, sprint_id: int) -> dict[str, Any]:
    """Get sprint metadata from Jira Agile API.

    Returns dict with id, name, state, startDate, endDate, goal, etc.
    """
    return self._request("GET", f"/rest/agile/1.0/sprint/{sprint_id}")
```

- [ ] **Step 2: Commit**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm
git add scripts/lib/jira_api.py
git commit -m "feat(jira-api): add get_sprint() for sprint metadata fetch"
```

---

## Task 2: add `get_all_sprints()` to AtlassianCache

**Files:**

- Modify: `mcp-servers/atlassian-cache/atlassian_cache/cache.py` (after `get_all_issues`, line ~841)
- Test: `tests/test_cache.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cache.py` (find the class that tests sprint methods, or add a new class):

```python
class TestGetAllSprints:
    def test_returns_empty_when_no_sprints(self, cache):
        assert cache.get_all_sprints() == []

    def test_returns_sprints_with_goals(self, cache):
        cache.put_sprint(1, {"name": "Sprint 1", "state": "active", "goal": "Ship coupon feature", "startDate": None, "endDate": None})
        cache.put_sprint(2, {"name": "Sprint 2", "state": "active", "goal": "Fix checkout flow", "startDate": None, "endDate": None})
        sprints = cache.get_all_sprints()
        assert len(sprints) == 2
        ids = {s["sprint_id"] for s in sprints}
        assert 1 in ids
        assert 2 in ids

    def test_excludes_sprints_without_goals(self, cache):
        cache.put_sprint(10, {"name": "Sprint 10", "state": "active", "goal": None, "startDate": None, "endDate": None})
        cache.put_sprint(11, {"name": "Sprint 11", "state": "active", "goal": "", "startDate": None, "endDate": None})
        assert cache.get_all_sprints() == []

    def test_returns_name_and_goal(self, cache):
        cache.put_sprint(5, {"name": "Sprint 5", "state": "active", "goal": "Improve performance", "startDate": None, "endDate": None})
        sprints = cache.get_all_sprints()
        assert sprints[0]["name"] == "Sprint 5"
        assert sprints[0]["goal"] == "Improve performance"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm/mcp-servers/atlassian-cache
.venv/bin/python -m pytest tests/test_cache.py::TestGetAllSprints -v
```

Expected: `AttributeError: 'AtlassianCache' object has no attribute 'get_all_sprints'`

- [ ] **Step 3: Implement `get_all_sprints()`**

Add to `atlassian_cache/cache.py` after `get_all_issues()` (line ~840):

```python
def get_all_sprints(self) -> list[dict]:
    """Return all cached sprints that have a goal (for reindex)."""
    rows = self.conn.execute(
        "SELECT sprint_id, name, goal FROM sprints WHERE goal IS NOT NULL AND goal != ''"
    ).fetchall()
    return [{"sprint_id": r["sprint_id"], "name": r["name"], "goal": r["goal"]} for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_cache.py::TestGetAllSprints -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add atlassian_cache/cache.py tests/test_cache.py
git commit -m "feat(cache): add get_all_sprints() for sprint goal reindex"
```

---

## Task 3: Sprint goal embedding + `cache_similar_sprints` tool

**Files:**

- Modify: `mcp-servers/atlassian-cache/server.py`
  - `handle_cache_sprint_issues` (~line 866): embed sprint goal after upstream fetch
  - Add `handle_cache_similar_sprints` (new function)
  - `handle_cache_reindex` (~line 1251): add sprint entity_type support
  - `TOOLS` list (~line 167): add `cache_similar_sprints` tool schema
  - `HANDLERS` dict (~line 1341): register new handler
  - top-level import block in `tests/test_server.py`: add new handler import
- Test: `tests/test_server.py`

### Step 1-4: Tests first

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_server.py` inside the `with patch.dict(...)` block, add import:

```python
handle_cache_similar_sprints,
```

Add these test classes:

```python
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

        # Verify goal was embedded
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
        # store_embedding should NOT have been called for sprint entity
        for call in mock_embeddings.store_embedding.call_args_list:
            assert "sprint::10" not in str(call)

    async def test_sprint_goal_skipped_when_embeddings_unavailable(self, cache, mock_jira_api):
        server.embeddings = None
        sprint_meta = {"id": 5, "name": "Sprint 5", "state": "active", "goal": "Some goal"}
        mock_jira_api.get_sprint.return_value = sprint_meta
        mock_jira_api.get_sprint_issues.return_value = {"issues": [], "total": 0}
        # Should not raise
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
        # Should return entity without sprint data, not crash
        assert result["results"][0]["entity_id"] == "sprint::999"
        assert "sprint" not in result["results"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_server.py::TestHandleSprintGoalEmbedding tests/test_server.py::TestHandleCacheSimilarSprints -v
```

Expected: `ImportError` or `AttributeError` (handler not yet added)

- [ ] **Step 3: Implement sprint goal embedding in `handle_cache_sprint_issues`**

In `server.py`, in the `if results is None:` block inside `handle_cache_sprint_issues` (after `embeddings.store_batch(all_issues)`, around line 920):

```python
            if embeddings and embeddings.available:
                await asyncio.to_thread(embeddings.store_batch, all_issues)
            # NEW: fetch + store sprint metadata, embed goal
            if jira_api:
                try:
                    sprint_meta = await asyncio.to_thread(jira_api.get_sprint, sprint_id)
                    c.put_sprint(sprint_id, sprint_meta)
                    goal = sprint_meta.get("goal") or ""
                    if goal and embeddings and embeddings.available:
                        sprint_name = sprint_meta.get("name", "")
                        embed_text = f"{sprint_name} goal: {goal}".strip()
                        await asyncio.to_thread(
                            embeddings.store_embedding,
                            f"sprint::{sprint_id}",
                            embed_text,
                            "sprint",
                        )
                except Exception as e:
                    logger.warning("Failed to fetch/embed sprint metadata %s: %s", sprint_id, e)
```

- [ ] **Step 4: Add `handle_cache_similar_sprints` function**

Add after `handle_cache_similar_issues` (~line 991) in `server.py`:

```python
async def handle_cache_similar_sprints(args: dict) -> str:
    """Semantic search for sprints by goal text."""
    if not embeddings or not embeddings.available:
        return json.dumps({"error": "Embeddings not available"})

    query = args["query"]
    limit = min(args.get("limit", 5), 20)
    similar = embeddings.find_similar(query, limit=limit, entity_type="sprint")

    enriched = []
    for item in similar:
        sprint_id_str = item["entity_id"].replace("sprint::", "")
        try:
            sprint_id = int(sprint_id_str)
        except ValueError:
            enriched.append(item)
            continue
        sprint = _require_cache().get_sprint(sprint_id, max_age_hours=_MAX_AGE_MAX)
        if sprint:
            enriched.append({**item, "sprint": sprint})
        else:
            enriched.append(item)

    return json.dumps({"results": enriched}, ensure_ascii=False)
```

- [ ] **Step 5: Add `_reindex_sprints()` helper and sprint reindex in `handle_cache_reindex`**

First, add a blocking helper after `_reindex_sections` (~line 1248) in `server.py`:

```python
def _reindex_sprints(sprints: list[dict]) -> int:
    """Blocking helper: store embeddings for sprint goals."""
    count = 0
    for s in sprints:
        embed_text = f"{s['name']} goal: {s['goal']}".strip()
        embeddings.store_embedding(f"sprint::{s['sprint_id']}", embed_text, entity_type="sprint")
        count += 1
    return count
```

Then in `handle_cache_reindex` (~line 1251), add sprint block. Change:

```python
    if entity_type in ("jira", "all"):
        issues = c.get_all_issues()
        count += await asyncio.to_thread(embeddings.store_batch, issues)
    if entity_type in ("confluence", "all") and confluence:
```

To:

```python
    if entity_type in ("jira", "all"):
        issues = c.get_all_issues()
        count += await asyncio.to_thread(embeddings.store_batch, issues)
    if entity_type in ("sprint", "all"):
        sprints = c.get_all_sprints()
        count += await asyncio.to_thread(_reindex_sprints, sprints)
    if entity_type in ("confluence", "all") and confluence:
```

- [ ] **Step 6: Add `cache_similar_sprints` to TOOLS list**

In `server.py` TOOLS list, add after `cache_similar_issues` Tool (~line 317):

```python
    Tool(
        name="cache_similar_sprints",
        description="Find sprints semantically similar to a query using vector embeddings on sprint goals. Returns sprints ranked by goal similarity. Requires sprint data to be cached first (via cache_sprint_issues).",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to find similar sprint goals for"},
                "limit": {"type": "integer", "description": "Max results (default: 5)", "default": 5},
            },
            "required": ["query"],
        },
    ),
```

- [ ] **Step 7: Update `cache_reindex` tool schema**

In TOOLS list, find the `cache_reindex` Tool (~line 436). Change the `entity_type` enum from:

```python
"enum": ["jira", "confluence", "all"]
```

To:

```python
"enum": ["jira", "sprint", "confluence", "all"]
```

- [ ] **Step 8: Register handler in HANDLERS dict**

In `server.py` HANDLERS dict, add after `cache_similar_issues`:

```python
    "cache_similar_sprints": handle_cache_similar_sprints,
```

- [ ] **Step 9: Add import to test_server.py**

Extend the **existing** `from server import (...)` list at lines 25-49 in `tests/test_server.py`.
Do NOT add a second `with patch.dict(...)` block. Just add one line to the existing list:

```python
        handle_cache_similar_sprints,
```

- [ ] **Step 10: Run all tests**

```bash
.venv/bin/python -m pytest tests/test_server.py::TestHandleSprintGoalEmbedding tests/test_server.py::TestHandleCacheSimilarSprints -v
```

Expected: all 6 tests pass

- [ ] **Step 11: Run full suite**

```bash
.venv/bin/python -m pytest -q 2>&1 | tail -5
```

Expected: all 287+ pass

- [ ] **Step 12: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(cache): sprint goal embedding + cache_similar_sprints tool"
```

---

## Task 4: `get_all_pages()` for ConfluenceCache

**Files:**

- Modify: `mcp-servers/atlassian-cache/atlassian_cache/confluence_cache.py`
- Test: `tests/test_confluence_cache.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_confluence_cache.py`:

```python
class TestGetAllPages:
    def test_returns_empty_when_no_pages(self, confluence_cache):
        assert confluence_cache.get_all_pages() == []

    def test_returns_page_metadata(self, confluence_cache):
        from tests.conftest import make_page
        confluence_cache.put_page(make_page(page_id="111", title="Coupon Design", labels=["design", "coupon"]))
        confluence_cache.put_page(make_page(page_id="222", title="Sprint Planning"))
        pages = confluence_cache.get_all_pages()
        assert len(pages) == 2
        ids = {p["page_id"] for p in pages}
        assert "111" in ids and "222" in ids

    def test_returns_labels_as_list(self, confluence_cache):
        from tests.conftest import make_page
        confluence_cache.put_page(make_page(page_id="333", title="Tagged Page", labels=["api", "backend"]))
        pages = confluence_cache.get_all_pages()
        page = next(p for p in pages if p["page_id"] == "333")
        assert isinstance(page["labels"], list)
        assert "api" in page["labels"]
        assert "backend" in page["labels"]

    def test_handles_null_labels(self, confluence_cache):
        from tests.conftest import make_page
        confluence_cache.put_page(make_page(page_id="444", title="No Labels"))
        pages = confluence_cache.get_all_pages()
        page = next(p for p in pages if p["page_id"] == "444")
        assert page["labels"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_confluence_cache.py::TestGetAllPages -v
```

Expected: `AttributeError`

- [ ] **Step 3: Implement `get_all_pages()`**

Add to `atlassian_cache/confluence_cache.py` (after `get_all_sections` or before `close`/`invalidate`):

```python
def get_all_pages(self) -> list[dict]:
    """Return all cached page metadata (for page-level reindex)."""
    rows = self.conn.execute(
        "SELECT page_id, title, labels FROM confluence_pages"
    ).fetchall()
    result = []
    for r in rows:
        labels = json.loads(r["labels"]) if r["labels"] else []
        result.append({"page_id": r["page_id"], "title": r["title"], "labels": labels})
    return result
```

Note: `json` is already imported at the top of `confluence_cache.py`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_confluence_cache.py::TestGetAllPages -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add atlassian_cache/confluence_cache.py tests/test_confluence_cache.py
git commit -m "feat(confluence-cache): add get_all_pages() for page-level reindex"
```

---

## Task 5: Confluence page-level embedding

**Files:**

- Modify: `mcp-servers/atlassian-cache/server.py`
  - `handle_cache_refresh_confluence` (~line 1193): embed page after storing
  - `handle_cache_invalidate_confluence` (~line 1187): remove page embedding on invalidate
  - `handle_cache_find_confluence_related` (~line 1167): include page-level results
  - `handle_cache_reindex` (~line 1251): add page-level embedding
  - Add `_reindex_pages()` helper (near `_reindex_sections`)
- Test: `tests/test_server.py`

### Entity convention

- entity_id: `f"page::{page_id}"` (e.g. `"page::12345"`)
- entity_type: `"confluence_page"`
- embed text: `f"{title} {' '.join(labels)}".strip()`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_server.py` inside the `with patch.dict(...)` block, add these imports:

```python
        handle_cache_find_confluence_related,
        handle_cache_invalidate_confluence,
        handle_cache_refresh_confluence,
        _reindex_pages,
```

Add these test classes:

```python
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
            "space": {"key": "BEP"},
            "_body_md": "## Overview\nContent",
            "version": {"number": 1, "when": "2026-01-01T00:00:00.000Z"},
            "metadata": {"labels": {"results": [{"name": "design"}, {"name": "coupon"}]}},
            "history": {"createdBy": {"displayName": "Alice"}},
            "_links": {"webui": "/wiki/spaces/BEP/pages/p1"},
        }

        await handle_cache_refresh_confluence({"page_id": "p1"})
        server.jira_api = None

        calls = [str(c) for c in mock_embeddings.store_embedding.call_args_list]
        assert any("page::p1" in c for c in calls)
        # Verify labels included in embedding text
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
            "id": "p2", "title": "Test", "space": {"key": "BEP"},
            "_body_md": "content",
            "version": {"number": 1, "when": "2026-01-01T00:00:00.000Z"},
            "metadata": {"labels": {"results": []}},
            "history": {"createdBy": {"displayName": "Bob"}},
            "_links": {"webui": "/wiki/spaces/BEP/pages/p2"},
        }
        # Should not raise
        result = json.loads(await handle_cache_refresh_confluence({"page_id": "p2"}))
        assert result["status"] == "refreshed"
        server.jira_api = None


class TestFindConfluenceRelatedWithPages:
    """cache_find_confluence_related returns both sections and page-level results."""

    async def test_includes_page_results(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.find_similar.side_effect = [
            [{"entity_id": "p1::overview", "entity_type": "confluence", "distance": 0.1}],
            [{"entity_id": "page::p2", "entity_type": "confluence_page", "distance": 0.15}],
        ]
        server.embeddings = mock_embeddings

        result = json.loads(await handle_cache_find_confluence_related({"query": "coupon", "limit": 5}))
        related = result["related"]
        entity_ids = [r["entity_id"] for r in related]
        assert "p1::overview" in entity_ids
        assert "page::p2" in entity_ids

    async def test_sorted_by_distance(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        mock_embeddings.find_similar.side_effect = [
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
        server.embeddings = mock_embeddings

        pages = conf.get_all_pages()
        count = _reindex_pages(pages)
        assert count == 1
        calls = [str(c) for c in mock_embeddings.store_embedding.call_args_list]
        assert any("page::x1" in c for c in calls)

    def test_returns_count(self, cache):
        from tests.conftest import make_page
        from atlassian_cache.confluence_cache import ConfluenceCache
        conf = ConfluenceCache(cache.conn, cache._lock)
        conf.put_page(make_page(page_id="y1", title="A"))
        conf.put_page(make_page(page_id="y2", title="B"))
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings
        pages = conf.get_all_pages()
        count = _reindex_pages(pages)
        assert count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_server.py::TestPageLevelEmbedding tests/test_server.py::TestFindConfluenceRelatedWithPages tests/test_server.py::TestReindexPages -v
```

Expected: ImportError or AttributeError

- [ ] **Step 3: Add `_reindex_pages()` helper in `server.py`**

Add after `_reindex_sections()` function (~line 1248):

```python
def _reindex_pages(pages: list[dict]) -> int:
    """Blocking helper: store page-level embeddings for Confluence pages."""
    count = 0
    for page in pages:
        title = page.get("title", "")
        labels = page.get("labels", [])
        embed_text = f"{title} {' '.join(labels)}".strip()
        if embed_text:
            embeddings.store_embedding(f"page::{page['page_id']}", embed_text, entity_type="confluence_page")
            count += 1
    return count
```

- [ ] **Step 4: Embed page in `handle_cache_refresh_confluence`**

In `handle_cache_refresh_confluence` (~line 1193), after `conf.put_page(page)`:

```python
    page = await asyncio.to_thread(jira_api.get_confluence_page, page_id)
    conf.put_page(page)
    # NEW: embed page title + labels
    if embeddings and embeddings.available:
        title = page.get("title", "")
        labels_results = page.get("metadata", {}).get("labels", {}).get("results", [])
        labels_str = " ".join(lbl["name"] for lbl in labels_results if "name" in lbl)
        embed_text = f"{title} {labels_str}".strip()
        if embed_text:
            await asyncio.to_thread(
                embeddings.store_embedding,
                f"page::{page_id}",
                embed_text,
                "confluence_page",
            )
    # Keep the existing return statement unchanged:
    return json.dumps({
        "status": "refreshed",
        "page_id": page_id,
        "title": page.get("title", ""),
    })
```

- [ ] **Step 5: Remove page embedding in `handle_cache_invalidate_confluence`**

In `handle_cache_invalidate_confluence` (~line 1187):

```python
async def handle_cache_invalidate_confluence(arguments: dict) -> str:
    conf = confluence or ConfluenceCache(_require_cache().conn, _require_cache()._lock)
    page_id = arguments["page_id"]
    conf.invalidate(page_id)
    # NEW: also remove page-level embedding
    if embeddings:
        embeddings.remove_embedding(f"page::{page_id}")
    return json.dumps({"invalidated": page_id})
```

- [ ] **Step 6: Update `handle_cache_find_confluence_related` to include page results**

Replace the current implementation (~line 1167):

```python
async def handle_cache_find_confluence_related(arguments: dict) -> str:
    limit = min(int(arguments.get("limit", 5)), 20)
    if not embeddings or not embeddings.available:
        return json.dumps({"related": []}, ensure_ascii=False)
    query = arguments["query"]
    section_results = embeddings.find_similar(query, limit=limit, entity_type="confluence")
    page_results = embeddings.find_similar(query, limit=limit, entity_type="confluence_page")
    combined = sorted(section_results + page_results, key=lambda x: x["distance"])[:limit]
    return json.dumps({"related": combined}, ensure_ascii=False)
```

- [ ] **Step 7: Add page reindex to `handle_cache_reindex`**

In `handle_cache_reindex`, after the sections reindex block:

```python
        if entity_type in ("confluence", "all") and confluence:
            sections = confluence.get_all_sections()
            count += await asyncio.to_thread(_reindex_sections, sections)
            # NEW: page-level embeddings
            pages = confluence.get_all_pages()
            count += await asyncio.to_thread(_reindex_pages, pages)
```

- [ ] **Step 8: Add imports to test_server.py**

`handle_cache_refresh_confluence` is **already** imported at line 43 of `test_server.py`. Do NOT add it again.

Add only these missing entries to the **existing** `from server import (...)` list (lines 25-49):

```python
        handle_cache_find_confluence_related,
        handle_cache_invalidate_confluence,
        _reindex_pages,
```

- [ ] **Step 9: Run failing tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_server.py::TestPageLevelEmbedding tests/test_server.py::TestFindConfluenceRelatedWithPages tests/test_server.py::TestReindexPages -v
```

Expected: all tests pass

- [ ] **Step 10: Run full suite**

```bash
.venv/bin/python -m pytest -q 2>&1 | tail -5
```

Expected: all pass

- [ ] **Step 11: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(cache): confluence page-level embedding (title+labels) via cache_refresh_confluence"
```

---

## Task 6: Include section heading in embedding text

**Files:**

- Modify: `mcp-servers/atlassian-cache/server.py`
  - `_reindex_sections()` (~line 1242): prepend heading to body_md
- Test: `tests/test_server.py`

This is intentionally the simplest task — one line change to the embedding text.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_server.py` (inside `with patch.dict(...)` block — `_reindex_sections` is already importable):

```python
class TestReindexSectionsWithHeading:
    """Section embedding text includes heading for better semantic search."""

    def test_heading_included_in_embedding_text(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings

        sections = [{"section_id": "p1::overview", "heading": "Overview", "body_md": "Some content"}]
        from server import _reindex_sections
        _reindex_sections(sections)

        call_args = mock_embeddings.store_embedding.call_args_list[0]
        text_arg = call_args[0][1]  # positional arg at index 1
        assert "Overview" in text_arg
        assert "Some content" in text_arg

    def test_heading_only_when_no_body(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings

        sections = [{"section_id": "p1::intro", "heading": "Introduction", "body_md": ""}]
        from server import _reindex_sections
        _reindex_sections(sections)

        call_args = mock_embeddings.store_embedding.call_args_list[0]
        text_arg = call_args[0][1]
        assert "Introduction" in text_arg

    def test_body_only_when_no_heading(self, cache):
        mock_embeddings = MagicMock()
        mock_embeddings.available = True
        server.embeddings = mock_embeddings

        sections = [{"section_id": "p1::sec", "body_md": "Just body content"}]
        from server import _reindex_sections
        _reindex_sections(sections)

        call_args = mock_embeddings.store_embedding.call_args_list[0]
        text_arg = call_args[0][1]
        assert "Just body content" in text_arg
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_server.py::TestReindexSectionsWithHeading -v
```

Expected: 2/3 tests fail (heading not currently in embedding text)

- [ ] **Step 3: Update `_reindex_sections()` in `server.py`**

Change the current implementation (~line 1242):

```python
# BEFORE:
def _reindex_sections(sections: list) -> int:
    """Blocking helper: store embeddings for Confluence sections."""
    count = 0
    for sec in sections:
        embeddings.store_embedding(sec["section_id"], sec["body_md"], entity_type="confluence")
        count += 1
    return count

# AFTER:
def _reindex_sections(sections: list) -> int:
    """Blocking helper: store embeddings for Confluence sections."""
    count = 0
    for sec in sections:
        heading = sec.get("heading", "")
        body = sec.get("body_md", "")
        embed_text = f"{heading}\n{body}".strip() if heading else body
        embeddings.store_embedding(sec["section_id"], embed_text, entity_type="confluence")
        count += 1
    return count
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_server.py::TestReindexSectionsWithHeading -v
```

Expected: 3 passed

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/python -m pytest -q 2>&1 | tail -5
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(cache): include section heading in confluence section embedding text"
```

---

## Final Verification

- [ ] **Run full test suite**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm/mcp-servers/atlassian-cache
.venv/bin/python -m pytest -v 2>&1 | tail -20
```

Expected: all tests pass (287+ with new tests added)

- [ ] **Verify TOOLS list is correct (no duplicate names)**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm/mcp-servers/atlassian-cache
python -c "import sys; sys.path.insert(0, '.'); from unittest.mock import MagicMock, patch
with patch.dict('sys.modules', {'lib.auth': MagicMock(), 'lib.jira_api': MagicMock()}):
    import server
    names = [t.name for t in server.TOOLS]
    print(names)
    assert len(names) == len(set(names)), 'Duplicate tool names!'
    assert 'cache_similar_sprints' in names
    print('OK:', len(names), 'tools')
"
```

Expected: prints tool list with `cache_similar_sprints` present, no duplicates

- [ ] **Final commit and push**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm
git log --oneline -8
git push
```
