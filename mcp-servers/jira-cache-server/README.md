---
user-invocable: false
---

# Jira Cache Server

MCP server providing local SQLite cache for Jira data. Reduces token consumption by caching issues, sprints, and search results locally with TTL expiration.

## Architecture

```text
Claude Code ──stdio──> jira-cache-server ──REST API──> Jira Cloud
                              │
                        SQLite + FTS5 + sqlite-vec
                        (~/.cache/jira-generator/jira.db)
```

**Key constraint:** MCP servers cannot call other MCP servers. This server uses JiraAPI (REST API v3) directly for upstream fetches, reusing `atlassian-scripts/lib/` for auth + API client.

## When to Use

- **Read issues** → `cache_get_issue` instead of MCP `jira_get_issue` (saves ~80% tokens because cached responses are compact)
- **Search** → `cache_search` / `cache_text_search` (instant local search, no API roundtrip)
- **Sprint overview** → `cache_sprint_issues` (full sprint in one call with pagination)
- **Dedup check** → `cache_similar_issues` (semantic similarity via embeddings)
- **After MCP writes** → `cache_invalidate(issue_key)` (HR6: stale reads corrupt verify/cascade/planning)
- **Stale data / user says "ล่าสุด"** → `cache_refresh(issue_key, force_refresh=true)`

## Tools (9)

| Tool | Description | Upstream? |
| ---- | ----------- | --------- |
| `cache_get_issue` | Get issue by key (cache-first) | Yes (on miss) |
| `cache_get_issues` | Batch get multiple issues | Yes (on miss) |
| `cache_search` | JQL search with caching | Yes (on miss) |
| `cache_sprint_issues` | All sprint issues with pagination | Yes (on miss) |
| `cache_text_search` | FTS5 keyword search (cache only) | No |
| `cache_similar_issues` | Semantic similarity (embeddings) | No |
| `cache_refresh` | Force-refresh from Jira | Yes |
| `cache_stats` | Cache hit/miss rates, size | No |
| `cache_invalidate` | Clear specific or all cache | No |

## TTL Strategy

| Data Type | Default TTL | Rationale |
| --------- | ----------- | --------- |
| Issues | 24 hours | Rarely change within sprint |
| Sprints | 4 hours | Sprint metadata is stable |
| Searches | 2 hours | Results may change with new issues |
| Embeddings | 7 days | Text doesn't change often |

## Setup

```bash
# 1. Install dependencies (uv manages the venv)
cd mcp-servers/jira-cache-server
uv sync --extra embeddings

# 2. Verify credentials exist
cat ~/.config/atlassian/.env
# Should have: CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN

# 3. Test server starts
uv run server.py
```

## Files

```text
mcp-servers/jira-cache-server/
├── server.py           # MCP entry point + 9 tool handlers
├── pyproject.toml      # Dependencies (core + embeddings + test extras)
└── jira_cache/
    ├── __init__.py     # Exports JiraCache, EmbeddingStore
    ├── cache.py        # SQLite + FTS5 cache (issues, sprints, searches)
    └── embeddings.py   # sqlite-vec + sentence-transformers
```

**Reused from `atlassian-scripts/lib/`:** `auth.py` (credentials), `jira_api.py` (REST API client), `exceptions.py`

## Usage Patterns

### Sprint Planning (biggest token saver)

```text
1. cache_sprint_issues(sprint_id=123)  → fetches + caches all issues
2. cache_get_issue("ABC-456")          → instant cache hit
3. cache_text_search("coupon")         → FTS5 search, no API call
4. cache_similar_issues("payment flow") → semantic search
```

### After Jira Updates

```text
cache_refresh(issue_keys=["ABC-456"])     → single issue
cache_refresh(sprint_id=123)              → entire sprint
cache_invalidate(sprint_id=123)           → clear stale data
```

### Token Savings Estimate

| Scenario | Without Cache | With Cache | Savings |
| -------- | ------------- | ---------- | ------- |
| Sprint overview (30 issues) | ~70K chars | ~70K first, 0 after | 80%+ |
| Issue lookup (repeated) | ~5K chars/call | ~5K first, 0 after | 90%+ |
| Keyword search | N/A | FTS5 local | 100% |
