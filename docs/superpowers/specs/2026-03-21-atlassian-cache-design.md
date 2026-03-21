# atlassian-cache MCP Server — Design Specification

**Date:** 2026-03-21
**Status:** Approved
**Scope:** Unified Jira + Confluence local cache with semantic search, section-level embeddings, and hybrid cache invalidation

---

## 1. Overview

The `atlassian-cache` MCP server replaces the current `jira-cache` server with a unified caching layer covering both Jira issues and Confluence pages. Its primary goal is to reduce Atlassian API calls and Claude token usage for AI agents navigating project context.

### Design Goals

| Goal | Target |
|------|--------|
| Jira token savings | ≥ 85% vs direct API |
| Confluence token savings | ≥ 78% vs direct API |
| In-session repeat savings | ≥ 95% via deduplication |
| Semantic search latency | < 100ms for 50k issues |
| Cross-modal search | Jira ↔ Confluence unified |

### Non-Goals

- Real-time sync (this is a read-optimised cache, not a replica)
- KV Cache (model-level, handled by Claude's prompt caching — separate concern)
- Full-text Thai language stemming (Thai is handled by vector search only)

---

## 2. Directory Rename

The server directory and all references migrate from `jira-cache` to `atlassian-cache`:

```
mcp-servers/jira-cache/          →  mcp-servers/atlassian-cache/
jira_cache/                      →  atlassian_cache/
pyproject.toml name: jira-cache  →  atlassian-cache
Server("jira-cache")             →  Server("atlassian-cache")
```

All 55+ references across `agents/`, `skills/`, `hooks/`, `scripts/`, `.mcp.json` must be updated.

---

## 3. Schema Evolution

Schema version is stored in `PRAGMA user_version`. Migrations run automatically on startup via `_migrate(conn)`.

### v4 — Confluence Tables (new in this release)

```sql
-- Confluence page metadata
CREATE TABLE confluence_pages (
    page_id     TEXT PRIMARY KEY,
    space_key   TEXT NOT NULL,
    title       TEXT NOT NULL,
    body_md     TEXT,               -- Markdown version (40-60% smaller than HTML/ADF)
    version_num INTEGER NOT NULL,   -- version.number from API
    version_when TEXT,              -- ISO timestamp of last edit
    labels      TEXT,               -- JSON array
    author      TEXT,
    cached_at   REAL NOT NULL,
    url         TEXT
);

-- Confluence inter-page links
CREATE TABLE confluence_links (
    from_page_id TEXT NOT NULL,
    to_page_id   TEXT NOT NULL,
    link_type    TEXT DEFAULT 'child',
    PRIMARY KEY (from_page_id, to_page_id)
);

-- Confluence search result cache
CREATE TABLE confluence_searches (
    search_key  TEXT PRIMARY KEY,   -- MD5 of query+params
    result_json TEXT NOT NULL,
    cached_at   REAL NOT NULL
);

-- Confluence page sections (H2-level granularity)
CREATE TABLE confluence_sections (
    section_id   TEXT PRIMARY KEY,  -- "{page_id}::{h2_heading_slug}"
    page_id      TEXT NOT NULL,
    heading      TEXT NOT NULL,
    body_md      TEXT NOT NULL,
    content_hash TEXT NOT NULL,     -- SHA256 of body_md for change detection
    cached_at    REAL NOT NULL,
    FOREIGN KEY (page_id) REFERENCES confluence_pages(page_id)
);

-- Vector embeddings (shared: Jira issues + Confluence sections)
CREATE VIRTUAL TABLE embeddings USING vec0(
    entity_id   TEXT,               -- issue_key or section_id
    entity_type TEXT,               -- "jira" | "confluence"
    embedding   FLOAT[384]          -- Phase 1: MiniLM 384d
);
```

### v5 — FTS5 Improvement

Migrate existing `issues_fts` to use `porter unicode61` tokenizer and add `labels_text` + `assignee_name` columns:

```sql
DROP TABLE IF EXISTS issues_fts;
CREATE VIRTUAL TABLE issues_fts USING fts5(
    issue_key UNINDEXED,
    summary,
    description_text,
    labels_text,
    assignee_name,
    content=issues,
    tokenize="porter unicode61"
);

CREATE VIRTUAL TABLE confluence_fts USING fts5(
    page_id UNINDEXED,
    title,
    body_text,
    labels_text,
    content=confluence_pages,
    tokenize="porter unicode61"
);
```

BM25 column weights (passed as `bm25(issues_fts, 10.0, 5.0, 2.0, 1.0)` in queries):

| Column | Weight |
|--------|--------|
| summary | 10.0 |
| description_text | 5.0 |
| labels_text | 2.0 |
| assignee_name | 1.0 |

### v6 — BGE-M3 Vector Migration (Phase 2, future)

Re-embed all entities at 1024 dimensions using `BAAI/bge-m3` with ONNX runtime:

```sql
DROP TABLE IF EXISTS embeddings;
CREATE VIRTUAL TABLE embeddings USING vec0(
    entity_id   TEXT,
    entity_type TEXT,
    embedding   FLOAT[1024]
);
```

Schema migration also updates `embedding_dim` entry in `cache_stats`.

---

## 4. Module Structure

```
mcp-servers/atlassian-cache/
├── pyproject.toml
├── server.py                           # MCP server entry point (21 tools)
└── atlassian_cache/
    ├── __init__.py
    ├── cache.py                        # JiraCache (existing, refactored)
    ├── confluence_cache.py             # ConfluenceCache (new)
    ├── embeddings.py                   # EmbeddingModel + cross-modal search (new)
    ├── sections.py                     # Section splitter + hash-based diff (new)
    └── migrations.py                   # Schema version management (extracted)
```

### Separation of Concerns

- `cache.py` — Jira issue CRUD, FTS search, sprint cache
- `confluence_cache.py` — Confluence page CRUD, section storage, Confluence FTS
- `embeddings.py` — Model lifecycle, embed/search for both entity types
- `sections.py` — H2-based Markdown splitter, SHA256 hash comparison
- `migrations.py` — `_migrate(conn)` with v1→v2→…→v6 step functions

---

## 5. Embedding Strategy

### Phase 1 (this release)

Model: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions)

- Drop-in replacement for current `all-MiniLM-L6-v2`
- Adds Thai/multilingual support with no schema change
- Loaded lazily; `embeddings` extra in `pyproject.toml` required
- `convert_to_tensor=False`, `normalize_embeddings=True`

### Phase 2 (future, v6 schema)

Model: `BAAI/bge-m3` via ONNX runtime (1024 dimensions)

- `sentence-transformers >= 3.0` with `backend="onnx"`
- Latency target: < 30ms per query embedding
- Requires schema migration + full re-index
- Exposed via `cache_reindex` tool

### Unified Cross-Modal Search

Both Jira issues and Confluence sections share the `embeddings` vec0 table. Queries can filter by `entity_type` or search across both:

```python
# Cross-modal: find Confluence context related to a Jira issue
results = embed_model.search(query_text, entity_type=None, limit=10)
# Returns mixed [{"entity_type": "jira", ...}, {"entity_type": "confluence", ...}]
```

---

## 6. Hybrid Cache Invalidation

Three layers operate independently and additively:

### Layer 1 — TTL Floor

- Issues: default `max_age_hours=1.0`, configurable per call
- Confluence pages: default `max_age_hours=4.0` (pages change less often)
- Searches: `max_age_hours=0.5` (short-lived, composition changes frequently)

### Layer 2 — Lazy Version-Check

Before returning cached content, fetch only the staleness signal from Atlassian API:

**Jira:** `GET /rest/api/3/issue/{key}?fields=updated` → compare `fields.updated` to `cached_at`
**Confluence:** `GET /wiki/rest/api/content/{id}?expand=version` → compare `version.number`

- Cost: ~50ms per check, ~200 tokens
- Skipped when `cached_at` is within TTL floor
- On stale detection: trigger full refresh, update cache, return fresh data

### Layer 3 — Write-Invalidation Hook

A PostToolUse hook fires after any MCP write tool (`jira_update_issue`, `jira_add_comment`, `confluence_update_page`, etc.) and calls `cache_invalidate(issue_key_or_page_id)` automatically.

Hook registration in `hooks/hooks.json`:

```json
{
  "PostToolUse": [{
    "matcher": "mcp__mcp-atlassian__.*",
    "hooks": [{"type": "command", "command": "python hooks/plugin/cache_write_invalidate.py '$TOOL_RESULT'"}]
  }]
}
```

---

## 7. Section-Level Confluence Embeddings

### Splitting Algorithm

Split Confluence pages at H2 headings (`##` in Markdown). Each section stored as `confluence_sections` row with:

- `section_id`: `"{page_id}::{slug}"` where slug = lowercase heading, spaces→hyphens
- `content_hash`: `sha256(body_md)` hex digest

### Partial Invalidation

On page update, re-split and compare hashes:

```
new_sections = split(page_md)
old_sections = db.get_sections(page_id)

for section in new_sections:
    if section.hash != old_sections.get(section.id).hash:
        re_embed(section)   # only changed sections

for section in old_sections - new_sections:
    db.delete_section(section.id)  # removed headings
```

Expected savings: ~80-90% of embedding cost when only one section changes.

---

## 8. FTS5 Improvements

### Tokenizer

`porter unicode61` — adds English stemming ("running" matches "run"), retains Unicode normalization. Thai content is not space-delimited; Thai is handled exclusively by vector search.

### BM25 Weights

Queries use `bm25(issues_fts, 10.0, 5.0, 2.0, 1.0)` for column-weighted relevance.

### New Fields

`labels_text` (space-joined label strings) and `assignee_name` added to FTS index. Both extracted at index time from structured `labels` JSON array and `assignee.displayName`.

---

## 9. SQLite PRAGMA Configuration

Applied once at connection open:

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-65536;   -- 64MB (negative = kilobytes)
PRAGMA mmap_size=268435456; -- 256MB
PRAGMA temp_store=MEMORY;
PRAGMA foreign_keys=ON;
```

WAL + synchronous=NORMAL: safe for concurrent reads, no fsync on every write. Target: sub-100ms FTS queries on 100k+ issues.

---

## 10. New and Updated Tools (21 total)

### Jira Tools (12)

| Tool | Change |
|------|--------|
| `cache_get_issue` | existing — add lazy version-check |
| `cache_get_issues` | existing — add lazy version-check, compact format |
| `cache_search` | existing — FTS5 improvements |
| `cache_sprint_issues` | existing — add compact format |
| `cache_invalidate` | existing — extend to Confluence entities |
| `cache_refresh` | existing |
| `cache_stats` | existing — add embedding stats |
| `cache_similar_issues` | existing — update model name |
| `cache_text_search` | existing |
| `cache_find_related` | **new** — convenience: given issue key, find similar Jira + Confluence |
| `cache_reindex` | **new** — re-embed all entities (for model migration) |
| `cache_sync` | **new** — incremental JQL sync by `updated >= timestamp` |

### Confluence Tools (9)

| Tool | Description |
|------|-------------|
| `cache_get_confluence_page` | Fetch page by ID; body_md stored in Markdown format |
| `cache_search_confluence` | FTS5 search across Confluence pages |
| `cache_get_confluence_children` | Get child pages of a given page_id |
| `cache_find_confluence_related` | Vector search: find Confluence sections similar to query |
| `cache_cross_search` | Cross-modal search: Jira + Confluence together |
| `cache_invalidate_confluence` | Invalidate a Confluence page cache entry |
| `cache_refresh_confluence` | Force-refresh a Confluence page from API |
| `cache_get_confluence_section` | Fetch a specific section by section_id |
| `cache_sprint_confluence` | Get Confluence pages linked to a sprint |

---

## 11. Token Optimisation Patterns

### In-Session Deduplication

Track returned entity keys per session in `_session_returned: set[str]`. On repeat fetch within the same session, return a compact reference (400 bytes) instead of full content (~8KB):

```json
{"key": "BEP-123", "summary": "...", "_cached": true, "_ref": "full data returned earlier this session"}
```

Expected savings: ~95% on repeated references within one agent execution.

### TOON Compact List Format

For responses with 20+ issues, use table-style compact format instead of object array:

```json
{
  "format": "compact",
  "headers": ["key", "summary", "status", "assignee", "sp"],
  "rows": [
    ["BEP-1", "Fix login bug", "In Progress", "{{SLOT_3}}", 3],
    ["BEP-2", "Add dark mode", "To Do", "{{SLOT_4}}", 5]
  ]
}
```

Expected savings: ~35-40% token reduction for 20+ issue lists.

---

## 12. Incremental Jira Sync (`cache_sync`)

```python
# Tool: cache_sync
# Args: project_key (str), since_hours (float = 24.0)

since = datetime.utcnow() - timedelta(hours=since_hours)
jql = f'project = {project_key} AND updated >= "{since.strftime("%Y-%m-%d %H:%M")}"'
# Fetch via jira_search, upsert into issues table, update FTS + embeddings
```

Avoids full project re-cache; only fetches recently modified issues. Suitable for background refresh hook.

---

## 13. pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "atlassian-cache"
version = "1.0.0"
description = "Unified Jira + Confluence cache MCP server with SQLite FTS5 + vector search"
requires-python = ">=3.11"
dependencies = ["mcp>=1.0.0,<2"]

[project.optional-dependencies]
embeddings = [
    "sqlite-vec>=0.1.1,<1",
    "sentence-transformers>=2.2.0,<4",
]
test = [
    "pytest>=8.0,<9",
    "pytest-asyncio>=0.24,<1",
    "pytest-cov>=6.0,<7",
]
```

---

## 14. MCP Server Entry Point

```python
# server.py

from contextlib import asynccontextmanager
from mcp.server import Server
from atlassian_cache.cache import JiraCache
from atlassian_cache.confluence_cache import ConfluenceCache

cache: JiraCache | None = None
confluence: ConfluenceCache | None = None

@asynccontextmanager
async def _lifespan(server: Server):
    global cache, confluence
    cache = JiraCache(db_path=DB_PATH)
    confluence = ConfluenceCache(cache.conn)  # shared connection
    try:
        yield
    finally:
        if cache:
            cache.close()

app = Server("atlassian-cache", lifespan=_lifespan)
```

Shared SQLite connection between `JiraCache` and `ConfluenceCache` — single WAL journal, no cross-module lock contention.

---

## 15. Testing Strategy

### Unit Tests

- `tests/test_cache.py` — Jira cache CRUD, FTS, sprint (existing, extend)
- `tests/test_confluence_cache.py` — Confluence page CRUD, section storage, FTS
- `tests/test_embeddings.py` — EmbeddingModel lazy load, search ranking
- `tests/test_sections.py` — H2 splitter, hash diff detection
- `tests/test_migrations.py` — v1→v6 migration chain

### Fixtures

`conftest.py` provides `tmp_db`, `cache`, `confluence_cache`, `sample_issue`, `sample_page`, `make_section`.

### Coverage

`fail_under = 100` in `pyproject.toml` — maintained. New modules must ship with tests.

### Similarity Thresholds (for test assertions)

| Use Case | Threshold |
|----------|-----------|
| Correctness-critical discovery | 0.88 – 0.92 |
| Exploratory "similar" queries | 0.75 – 0.82 |

---

## 16. Implementation Phases

| Phase | Deliverable |
|-------|-------------|
| 1 | Directory rename `jira-cache` → `atlassian-cache`, module rename, all 55+ ref updates |
| 2 | Schema migrations v4 (Confluence tables) + v5 (FTS5 porter tokenizer) |
| 3 | `confluence_cache.py` + `sections.py` modules with tests |
| 4 | `embeddings.py` — multilingual MiniLM Phase 1, cross-modal search |
| 5 | 9 new Confluence MCP tools in `server.py` |
| 6 | 3 new Jira tools: `cache_find_related`, `cache_reindex`, `cache_sync` |
| 7 | In-session deduplication + TOON compact format |
| 8 | Hybrid invalidation: TTL upgrade + lazy version-check + write-hook |
| 9 | PRAGMA optimisation + SQLite WAL tuning |
| 10 | Integration tests, coverage ≥ 100%, doctor script update |

---

## 17. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `sqlite-vec` not installed | Graceful degradation: vector tools return error message, FTS still works |
| Embedding model download on first use | Warn in `cache_stats`, suggest `uv sync --extra embeddings` |
| Confluence body > 1MB | Store up to 500KB of Markdown body; truncate at natural section boundary |
| BGE-M3 ONNX latency regression | Keep MiniLM Phase 1 as fallback; `cache_reindex --model miniLM` to rollback |
| Cross-modal search quality | Validate with smoke queries after `cache_reindex`; threshold config in `cache_stats` |
