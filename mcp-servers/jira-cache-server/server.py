# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp>=1.0.0,<2",
#     "sqlite-vec>=0.1.1,<1",
#     "sentence-transformers>=2.2.0,<4",
# ]
# ///
"""MCP server for Jira data caching with FTS5 and vector search.

Provides 10 tools for cached Jira data access:
- cache_get_issue: Get issue (cache-first, upstream fallback, compact mode)
- cache_get_issues: Batch get multiple issues (single MCP call)
- cache_search: JQL search with caching
- cache_sprint_issues: Sprint issues with caching
- cache_text_search: FTS5 keyword search on cached issues
- cache_similar_issues: Semantic similarity via embeddings
- cache_refresh: Force-refresh from upstream
- cache_stats: Cache statistics
- cache_invalidate: Clear cache entries (with optional auto_refresh)

Runs as stdio MCP server for Claude Code integration.

Usage:
    uv run server.py
"""

import asyncio
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Add atlassian-scripts to path for JiraAPI + auth reuse
# Plugin mode: PYTHONPATH set via .mcp.json env (${CLAUDE_PLUGIN_ROOT}/skills/atlassian-scripts)
# Fallback for standalone testing: resolve relative to new location (mcp-servers/jira-cache-server/ -> root -> skills/)
_scripts_dir = Path(__file__).resolve().parent.parent.parent / "skills" / "atlassian-scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

# Local imports (jira_cache to avoid namespace collision with atlassian-scripts/lib)
from jira_cache.cache import JiraCache, strip_noise
from jira_cache.embeddings import EmbeddingStore, embedding_text as _embedding_text
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("jira-cache-server")

# Claude Code MCP token limit is ~30K chars; keep well under
MAX_RESPONSE_CHARS = 25_000

# Safety guard: max pages for sprint pagination (prevents infinite loops)
MAX_SPRINT_PAGES = 20

# Limit caps for search tools
MAX_TEXT_SEARCH_LIMIT = 50
MAX_SIMILAR_LIMIT = 20
MAX_ISSUE_KEYS_BATCH = 100

# H4: Validate issue key format at MCP boundary (prevent injection)
_ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{0,9}-\d{1,6}$")


def _validate_issue_key(key: str) -> str:
    """Validate issue key format. Returns key if valid, raises ValueError otherwise."""
    if not isinstance(key, str) or not _ISSUE_KEY_RE.match(key):
        raise ValueError(f"Invalid issue key: {key!r}")
    return key


# --- Globals (initialized on startup) ---
cache: JiraCache | None = None
embeddings: EmbeddingStore | None = None
jira_api: JiraAPI | None = None


# H6: Safe global accessors (prevent NoneType crashes)
def _require_cache() -> JiraCache:
    """Get cache or raise RuntimeError."""
    if cache is None:
        raise RuntimeError("Cache not initialized")
    return cache


TOOLS = [
    Tool(
        name="cache_get_issue",
        description="Get a Jira issue by key. Returns cached data if fresh, otherwise fetches from Jira REST API and caches the result. Use compact=true for minimal response (key, summary, status, assignee only).",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Jira issue key (e.g., BEP-123)"},
                "fields": {
                    "type": "string",
                    "description": "Comma-separated fields for upstream fetch (default: summary,status,assignee,issuetype,priority,labels,parent,description)",
                    "default": "summary,status,assignee,issuetype,priority,labels,parent,description",
                },
                "max_age_hours": {
                    "type": "number",
                    "description": "Max cache age in hours (default: 24)",
                    "default": 24,
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Skip cache and fetch from Jira upstream, then update cache (default: false)",
                    "default": False,
                },
                "compact": {
                    "type": "boolean",
                    "description": "Return minimal fields only: key, summary, status, assignee, issuetype, priority, labels, parent (~200 chars vs ~5KB). Use for overviews. (default: false)",
                    "default": False,
                },
            },
            "required": ["issue_key"],
        },
    ),
    # P1-F: Batch get issues tool
    Tool(
        name="cache_get_issues",
        description="Get multiple Jira issues in one call. Returns cached data for fresh issues, fetches missing ones from upstream. Much more efficient than calling cache_get_issue multiple times. Use compact=true for minimal responses.",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of Jira issue keys (e.g., ['BEP-123', 'BEP-456'])",
                },
                "fields": {
                    "type": "string",
                    "description": "Comma-separated fields for upstream fetch (default: summary,status,assignee,issuetype,priority,labels,parent,description)",
                    "default": "summary,status,assignee,issuetype,priority,labels,parent,description",
                },
                "max_age_hours": {
                    "type": "number",
                    "description": "Max cache age in hours (default: 24)",
                    "default": 24,
                },
                "compact": {
                    "type": "boolean",
                    "description": "Return minimal fields only (default: false)",
                    "default": False,
                },
            },
            "required": ["issue_keys"],
        },
    ),
    Tool(
        name="cache_search",
        description="Search Jira issues via JQL. Returns cached results if same query was recently run, otherwise fetches from Jira REST API. Always use fields and limit params to control response size.",
        inputSchema={
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL query string"},
                "fields": {
                    "type": "string",
                    "description": "Comma-separated fields (default: summary,status,assignee,issuetype,priority)",
                    "default": "summary,status,assignee,issuetype,priority",
                },
                "limit": {"type": "integer", "description": "Max results (default: 30, max: 50)", "default": 30},
                "max_age_hours": {"type": "number", "description": "Max cache age in hours (default: 2)", "default": 2},
                "force_refresh": {
                    "type": "boolean",
                    "description": "Skip cache and fetch from Jira upstream, then update cache (default: false)",
                    "default": False,
                },
                "start_at": {
                    "type": "integer",
                    "description": "Response offset for pagination. Use when previous response had has_more=true (default: 0)",
                    "default": 0,
                },
            },
            "required": ["jql"],
        },
    ),
    Tool(
        name="cache_sprint_issues",
        description="Get all issues in a sprint. Uses Jira Agile API with caching. Good for sprint overviews and capacity planning.",
        inputSchema={
            "type": "object",
            "properties": {
                "sprint_id": {"type": ["integer", "string"], "description": "Jira sprint ID (e.g., 123)"},
                "fields": {
                    "type": "string",
                    "description": "Comma-separated fields (default: summary,status,assignee,issuetype,priority,labels)",
                    "default": "summary,status,assignee,issuetype,priority,labels",
                },
                "max_age_hours": {"type": "number", "description": "Max cache age in hours (default: 2)", "default": 2},
                "force_refresh": {
                    "type": "boolean",
                    "description": "Skip cache and fetch from Jira upstream, then update cache (default: false)",
                    "default": False,
                },
                "start_at": {
                    "type": "integer",
                    "description": "Response offset for pagination. Use when previous response had has_more=true (default: 0)",
                    "default": 0,
                },
            },
            "required": ["sprint_id"],
        },
    ),
    Tool(
        name="cache_text_search",
        description="Full-text keyword search on cached Jira issues using FTS5. Searches summary and description text. No upstream call — only returns previously cached issues.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords (supports FTS5 syntax: AND, OR, NOT, quotes for phrases)",
                },
                "limit": {"type": "integer", "description": "Max results (default: 10)", "default": 10},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="cache_similar_issues",
        description="Find semantically similar issues using vector embeddings. Requires sqlite-vec and sentence-transformers. Returns issues ranked by cosine similarity.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to find similar issues for"},
                "limit": {"type": "integer", "description": "Max results (default: 5)", "default": 5},
                "exclude_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Issue keys to exclude from results",
                    "default": [],
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="cache_refresh",
        description="Force-refresh issue(s) from Jira upstream, ignoring cache. Use after making changes to issues or when cache is stale.",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Issue keys to refresh (e.g., ['BEP-123', 'BEP-456'])",
                },
                "sprint_id": {
                    "type": "integer",
                    "description": "Refresh all issues in this sprint (alternative to issue_keys)",
                },
            },
        },
    ),
    Tool(
        name="cache_stats",
        description="Get cache statistics: issue count, hit/miss rate, database size, oldest/newest entries, schema version, purge counts.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="cache_invalidate",
        description="Clear cache entries. Can invalidate specific issues, a sprint, or the entire cache. Use auto_refresh=true to invalidate AND immediately re-fetch from upstream in one call (saves an extra MCP round-trip).",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Invalidate a specific issue"},
                "sprint_id": {"type": "integer", "description": "Invalidate all issues in a sprint"},
                "all": {
                    "type": "boolean",
                    "description": "Clear entire cache (requires confirm=true)",
                    "default": False,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Safety guard: must be true when using all=true",
                    "default": False,
                },
                "auto_refresh": {
                    "type": "boolean",
                    "description": "After invalidating, immediately re-fetch from upstream and cache the result (default: false). Reduces 2 MCP calls to 1.",
                    "default": False,
                },
            },
        },
    ),
]


def _init() -> None:
    """Initialize cache, embeddings, and upstream API client."""
    global cache, embeddings, jira_api

    cache = JiraCache()
    # C3: Pass shared write lock so EmbeddingStore serialises SQLite writes with JiraCache
    embeddings = EmbeddingStore(cache.conn, cache._lock)

    try:
        creds = load_credentials()
        jira_url = derive_jira_url(creds["CONFLUENCE_URL"])
        auth_header = get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"])
        ssl_ctx = create_ssl_context()
        jira_api = JiraAPI(base_url=jira_url, auth_header=auth_header, ssl_context=ssl_ctx)
        logger.info("Initialized: cache=%s, embeddings=%s, upstream=%s", cache.db_path, embeddings.available, jira_url)
    except Exception as e:
        logger.error("Failed to init upstream API (cache-only mode): %s", e)
        jira_api = None


def _extract_core_fields(issue: dict) -> dict:
    """Extract core display fields shared by summary formatting and compact mode."""
    fields = issue.get("fields", {})
    status = fields.get("status", {})
    assignee = fields.get("assignee", {})
    issuetype = fields.get("issuetype", {})
    return {
        "key": issue.get("key", "?"),
        "summary": fields.get("summary", ""),
        "status": status.get("name", "") if isinstance(status, dict) else str(status),
        "assignee": assignee.get("displayName", "Unassigned") if isinstance(assignee, dict) else str(assignee or "Unassigned"),
        "issuetype": issuetype.get("name", "") if isinstance(issuetype, dict) else str(issuetype),
    }


def _format_issue_summary(issue: dict) -> str:
    """Format issue data for compact MCP response."""
    c = _extract_core_fields(issue)
    return f"[{c['key']}] ({c['issuetype']}) {c['summary']} | {c['status']} | {c['assignee']}"


# --- P2-B: Compact mode extraction ---


def _compact_issue(issue: dict) -> dict:
    """Extract minimal fields from a full issue dict."""
    compact = _extract_core_fields(issue)
    fields = issue.get("fields", {})
    if "priority" in fields:
        p = fields["priority"]
        compact["priority"] = p.get("name", "") if isinstance(p, dict) else str(p)
    if "labels" in fields:
        compact["labels"] = fields["labels"]
    if "parent" in fields:
        p = fields["parent"]
        compact["parent"] = p.get("key", "") if isinstance(p, dict) else str(p)
    return compact


# --- Response size management (tiered: strip → paginate → compact) ---


def _strip_response_noise(result_json: str) -> str:
    """Level 1: Strip Jira metadata noise from JSON response."""
    try:
        data = json.loads(result_json)
    except (json.JSONDecodeError, TypeError):
        return result_json
    stripped = strip_noise(data)
    return json.dumps(stripped, ensure_ascii=False)


def _find_issues_list(data: dict) -> tuple[list[dict] | None, dict | None, str | None]:
    """Find the issues array in common response shapes."""
    for parent_key in ("results", None):
        container = data.get(parent_key) if parent_key else data
        if isinstance(container, dict):
            for k in ("issues", "data"):
                if isinstance(container.get(k), list):
                    return container[k], container, k
    return None, None, None


def _paginate_response(result_json: str, tool_name: str = "") -> str:
    """Level 2: Return a subset of issues that fits within MAX_RESPONSE_CHARS."""
    try:
        data = json.loads(result_json)
    except (json.JSONDecodeError, TypeError):
        return result_json[:MAX_RESPONSE_CHARS] + "\n... (truncated)"

    issues, parent, key = _find_issues_list(data)
    if issues is None:
        return result_json[:MAX_RESPONSE_CHARS] + "\n... (truncated)"

    total = len(issues)
    # Estimate how many issues fit based on average size
    avg_size = len(result_json) / max(total, 1)
    fits = max(1, int((MAX_RESPONSE_CHARS - 500) / avg_size))  # 500 for metadata overhead
    fits = min(fits, total)

    parent[key] = issues[:fits]
    # M5: Only suggest start_at pagination for tools that actually support the parameter
    if "start_at" in _TOOL_SCHEMAS.get(tool_name, {}):
        hint = f"Call again with start_at={fits} to get next page"
    else:
        hint = f"Reduce batch size — returned {fits} of {total} items"
    data["_pagination"] = {
        "total": total,
        "returned": fits,
        "has_more": fits < total,
        "next_offset": fits,
        "hint": hint,
    }

    result = json.dumps(data, ensure_ascii=False)
    # Safety: halve if still too large
    while len(result) > MAX_RESPONSE_CHARS and fits > 1:
        fits = fits // 2
        parent[key] = issues[:fits]
        data["_pagination"].update({"returned": fits, "next_offset": fits, "has_more": True})
        result = json.dumps(data, ensure_ascii=False)

    return result


def _compact_response(result_json: str) -> str:
    """Level 3 (last resort): Replace full issues with minimal summaries."""
    try:
        data = json.loads(result_json)
    except (json.JSONDecodeError, TypeError):
        return result_json[:MAX_RESPONSE_CHARS] + "\n... (truncated)"

    issues, parent, key = _find_issues_list(data)
    if issues is None:
        return result_json[:MAX_RESPONSE_CHARS] + "\n... (truncated)"

    compact_issues = []
    for issue in issues:
        if isinstance(issue, dict) and "fields" in issue:
            compact_issues.append(_compact_issue(issue))
        else:
            compact_issues.append(issue)

    parent[key] = compact_issues
    data["_compacted"] = True
    data["_original_chars"] = len(result_json)
    return json.dumps(data, ensure_ascii=False)


# --- P3: Upstream fetch timing ---


def _timed_upstream(label: str, func: Any, *args: Any, **kwargs: Any) -> Any:
    """Call func with timing logged at INFO level."""
    t0 = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        logger.info("Upstream %s: %.1fms", label, elapsed * 1000)
        return result
    except Exception:
        elapsed = time.perf_counter() - t0
        logger.warning("Upstream %s FAILED after %.1fms", label, elapsed * 1000)
        raise


# --- Tool Handlers ---


async def handle_cache_get_issue(args: dict) -> str:
    """Get issue: cache-first with upstream fallback + stale fallback."""
    c = _require_cache()
    try:
        issue_key = _validate_issue_key(args["issue_key"])
    except ValueError as e:
        return json.dumps({"error": str(e)})
    fields = args.get("fields", "summary,status,assignee,issuetype,priority,labels,parent,description")
    max_age_raw = args.get("max_age_hours")
    max_age = max_age_raw if max_age_raw is not None else c.get_adaptive_ttl(issue_key)
    force_refresh = args.get("force_refresh", False)
    compact = args.get("compact", False)

    # Try cache first (skip if force_refresh)
    if not force_refresh:
        cached = c.get_issue(issue_key, max_age_hours=max_age)
        if cached:
            logger.info("Cache HIT: %s", issue_key)
            issue_data = _compact_issue(cached) if compact else cached
            return json.dumps({"source": "cache", "issue": issue_data}, ensure_ascii=False)

    # Cache miss or force_refresh — fetch upstream
    if not jira_api:
        # P2-D: Stale fallback when upstream unavailable
        stale = c.get_issue_stale(issue_key)
        if stale:
            issue_data = _compact_issue(stale) if compact else stale
            return json.dumps(
                {
                    "source": "stale_cache",
                    "warning": "Upstream API not available, returning stale data",
                    "issue": issue_data,
                },
                ensure_ascii=False,
            )
        return json.dumps({"error": "Issue not in cache and upstream API not available"})

    logger.info("Cache %s: %s — fetching upstream", "REFRESH" if force_refresh else "MISS", issue_key)
    try:
        issue = _timed_upstream(f"get_issue({issue_key})", jira_api.get_issue, issue_key, fields=fields)
        c.put_issue(issue_key, issue)
        # C4: Run CPU-bound model inference off the event loop to avoid blocking
        if embeddings and embeddings.available:
            await asyncio.to_thread(embeddings.store_embedding, issue_key, _embedding_text(issue))
        issue_data = _compact_issue(issue) if compact else issue
        return json.dumps({"source": "upstream", "issue": issue_data}, ensure_ascii=False)
    except Exception as e:
        # P2-D: Stale fallback on upstream error
        stale = c.get_issue_stale(issue_key)
        if stale:
            issue_data = _compact_issue(stale) if compact else stale
            return json.dumps(
                {
                    "source": "stale_cache",
                    "warning": f"Upstream failed ({type(e).__name__}: {str(e)[:200]}), returning stale data",
                    "issue": issue_data,
                },
                ensure_ascii=False,
            )
        return json.dumps({"error": f"Failed to fetch {issue_key}: {type(e).__name__}: {str(e)[:200]}"})


# --- P1-F: Batch get issues handler ---


async def handle_cache_get_issues(args: dict) -> str:
    """Batch get multiple issues: cache-first, upstream for misses."""
    c = _require_cache()
    issue_keys = args.get("issue_keys", [])
    if not issue_keys:
        return json.dumps({"error": "issue_keys is required and must be non-empty"})

    # Cap batch size to prevent excessive upstream calls
    issue_keys = issue_keys[:MAX_ISSUE_KEYS_BATCH]

    # S1: Validate key format — mirrors single-issue path (batch path previously skipped this)
    valid_keys: list[str] = []
    invalid_keys: list[str] = []
    for k in issue_keys:
        try:
            valid_keys.append(_validate_issue_key(k))
        except ValueError:
            invalid_keys.append(k)
    issue_keys = valid_keys
    if not issue_keys:
        return json.dumps({"error": f"No valid issue keys provided. Invalid: {invalid_keys}"})

    fields = args.get("fields", "summary,status,assignee,issuetype,priority,labels,parent,description")
    max_age = args.get("max_age_hours", 24)
    compact = args.get("compact", False)

    # Batch get from cache
    found_issues, missing_keys = c.get_issues_batch(issue_keys, max_age_hours=max_age)

    # Fetch missing from upstream — concurrent HTTP via asyncio.to_thread
    upstream_issues = []
    if missing_keys and jira_api:
        async def _fetch_one(key: str) -> tuple[str, dict | None, str | None]:
            try:
                t0 = time.perf_counter()
                issue = await asyncio.to_thread(jira_api.get_issue, key, fields=fields)
                logger.info("Upstream get_issue(%s): %.1fms", key, (time.perf_counter() - t0) * 1000)
                return key, issue, None
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", key, exc)
                return key, None, str(exc)

        fetch_results = await asyncio.gather(*[_fetch_one(k) for k in missing_keys])

        # Store results serially — SQLite conn is not safe to use from multiple threads concurrently
        new_issues = []
        for key, issue, _err in fetch_results:
            if issue:
                c.put_issue(key, issue)
                new_issues.append(issue)
                upstream_issues.append(issue)
            else:
                stale = c.get_issue_stale(key)
                if stale:
                    upstream_issues.append(stale)
        # Batch encode + store embeddings off the event loop (model inference is CPU-bound)
        if new_issues and embeddings and embeddings.available:
            await asyncio.to_thread(embeddings.store_batch, new_issues)

    all_issues = found_issues + upstream_issues

    if compact:
        all_issues = [_compact_issue(i) for i in all_issues]

    result: dict = {
        "source": "batch",
        "total": len(all_issues),
        "from_cache": len(found_issues),
        "from_upstream": len(upstream_issues),
        "still_missing": [k for k in missing_keys if k not in {i.get("key") for i in upstream_issues}],
        "issues": all_issues,
    }
    if invalid_keys:
        result["invalid_keys"] = invalid_keys
    return json.dumps(result, ensure_ascii=False)


async def handle_cache_search(args: dict) -> str:
    """JQL search with caching."""
    c = _require_cache()
    jql = args["jql"]
    fields = args.get("fields", "summary,status,assignee,issuetype,priority")
    limit = min(args.get("limit", 30), 50)
    max_age = args.get("max_age_hours", 2)
    force_refresh = args.get("force_refresh", False)
    start_at = args.get("start_at", 0)

    source = "cache"
    results = None

    # Try cache (skip if force_refresh)
    if not force_refresh:
        cached = c.get_search(jql, fields, limit, max_age_hours=max_age)
        if cached:
            logger.info("Search cache HIT: %s", jql[:60])
            results = cached

    # Cache miss or force_refresh — fetch upstream
    if results is None:
        if not jira_api:
            return json.dumps({"error": "Search not in cache and upstream API not available"})

        logger.info("Search cache MISS: %s — fetching upstream", jql[:60])
        try:
            results = _timed_upstream(
                f"search({jql[:40]})", jira_api.search_issues, jql, fields=fields, max_results=limit
            )
            c.put_search(jql, fields, limit, results)
            if embeddings and embeddings.available:
                embeddings.store_batch(results.get("issues", []))
            source = "upstream"
        except Exception as e:
            return json.dumps({"error": f"Search failed: {type(e).__name__}: {str(e)[:200]}"})

    # Apply response-level offset (pagination page 2+)
    if start_at > 0:
        issues = results.get("issues", [])
        results = {**results, "issues": issues[start_at:], "startAt": start_at}

    return json.dumps({"source": source, "results": results}, ensure_ascii=False)


async def handle_cache_sprint_issues(args: dict) -> str:
    """Get sprint issues with caching."""
    c = _require_cache()
    sprint_id = args["sprint_id"]
    # S7: Ensure sprint_id is an integer before interpolating into JQL to prevent injection
    if not isinstance(sprint_id, int):
        return json.dumps({"error": f"sprint_id must be an integer, got: {type(sprint_id).__name__}"})
    fields = args.get("fields", "summary,status,assignee,issuetype,priority,labels")
    max_age = args.get("max_age_hours", 2)
    force_refresh = args.get("force_refresh", False)
    response_offset = args.get("start_at", 0)

    source = "cache"
    results = None

    # Use JQL-based search cache (sprint issues = search query)
    jql = f"sprint = {sprint_id}"
    if not force_refresh:
        cached = c.get_search(jql, fields, 50, max_age_hours=max_age)
        if cached:
            logger.info("Sprint cache HIT: %s", sprint_id)
            results = cached

    if results is None:
        if not jira_api:
            return json.dumps({"error": "Sprint not in cache and upstream API not available"})

        logger.info("Sprint cache MISS: %s — fetching upstream", sprint_id)
        try:
            all_issues: list[dict] = []
            upstream_offset = 0
            pages_fetched = 0
            while pages_fetched < MAX_SPRINT_PAGES:
                page = _timed_upstream(
                    f"sprint({sprint_id}, offset={upstream_offset})",
                    jira_api.get_sprint_issues,
                    sprint_id,
                    fields=fields,
                    max_results=50,
                    start_at=upstream_offset,
                )
                issues = page.get("issues", [])
                all_issues.extend(issues)
                pages_fetched += 1
                if not issues or upstream_offset + len(issues) >= page.get("total", 0):
                    break
                upstream_offset += len(issues)

            results = {"issues": all_issues, "total": len(all_issues)}
            c.put_search(jql, fields, 50, results, sprint_id=sprint_id)
            if embeddings and embeddings.available:
                embeddings.store_batch(all_issues)
            source = "upstream"
        except Exception as e:
            return json.dumps({"error": f"Sprint fetch failed: {type(e).__name__}: {str(e)[:200]}"})

    # Apply response-level offset (pagination page 2+)
    if response_offset > 0:
        issues = results.get("issues", [])
        results = {**results, "issues": issues[response_offset:], "startAt": response_offset}

    return json.dumps({"source": source, "results": results}, ensure_ascii=False)


async def handle_cache_text_search(args: dict) -> str:
    """FTS5 keyword search on cached issues."""
    c = _require_cache()
    query = args["query"]
    limit = min(args.get("limit", 10), MAX_TEXT_SEARCH_LIMIT)

    results = c.text_search(query, limit=limit)
    summaries = [_format_issue_summary(r) for r in results]

    return json.dumps(
        {
            "source": "fts5",
            "count": len(results),
            "issues": summaries,
        },
        ensure_ascii=False,
    )


async def handle_cache_similar_issues(args: dict) -> str:
    """Semantic similarity search via embeddings."""
    if not embeddings or not embeddings.available:
        return json.dumps({"error": "Embeddings not available (install sqlite-vec and sentence-transformers)"})

    query = args["query"]
    limit = min(args.get("limit", 5), MAX_SIMILAR_LIMIT)
    exclude = args.get("exclude_keys", [])

    similar = embeddings.find_similar(query, limit=limit, exclude_keys=exclude)

    # Enrich with issue data from cache
    enriched = []
    for item in similar:
        issue = _require_cache().get_issue(item["issue_key"], max_age_hours=9999)
        if issue:
            enriched.append(
                {
                    **item,
                    "summary": _format_issue_summary(issue),
                }
            )
        else:
            enriched.append(item)

    return json.dumps(
        {
            "source": "embeddings",
            "count": len(enriched),
            "results": enriched,
        },
        ensure_ascii=False,
    )


async def handle_cache_refresh(args: dict) -> str:
    """Force-refresh from upstream."""
    c = _require_cache()
    if not jira_api:
        return json.dumps({"error": "Upstream API not available"})

    issue_keys = args.get("issue_keys", [])
    sprint_id = args.get("sprint_id")

    # SILENT-NOOP: Return clear error instead of misleading {"refreshed": 0}
    if not issue_keys and sprint_id is None:
        return json.dumps({"error": "Specify issue_keys or sprint_id"})

    refreshed = []

    # Refresh specific issues — concurrent HTTP via asyncio.to_thread
    if issue_keys:
        async def _refresh_one(key: str) -> tuple[str, dict | None]:
            try:
                t0 = time.perf_counter()
                issue = await asyncio.to_thread(jira_api.get_issue, key)
                logger.info("Upstream refresh(%s): %.1fms", key, (time.perf_counter() - t0) * 1000)
                return key, issue
            except Exception as exc:
                logger.error("Failed to refresh %s: %s", key, exc)
                return key, None

        refresh_results = await asyncio.gather(*[_refresh_one(k) for k in issue_keys])
        # Store serially — SQLite conn not safe from multiple threads concurrently
        refreshed_issues = []
        for key, issue in refresh_results:
            if issue:
                c.put_issue(key, issue)
                refreshed_issues.append(issue)
                refreshed.append(key)
        # Batch encode + store embeddings off the event loop (model inference is CPU-bound)
        if refreshed_issues and embeddings and embeddings.available:
            await asyncio.to_thread(embeddings.store_batch, refreshed_issues)

    # Refresh sprint
    if sprint_id:
        try:
            c.invalidate_sprint(sprint_id)
            start_at = 0
            pages_fetched = 0
            while pages_fetched < MAX_SPRINT_PAGES:
                page = _timed_upstream(
                    f"refresh_sprint({sprint_id}, offset={start_at})",
                    jira_api.get_sprint_issues,
                    sprint_id,
                    max_results=50,
                    start_at=start_at,
                )
                issues = page.get("issues", [])
                c.put_issues_batch(issues)
                if embeddings and embeddings.available:
                    embeddings.store_batch(issues)
                refreshed.extend(i.get("key", "") for i in issues)
                pages_fetched += 1
                if not issues or start_at + len(issues) >= page.get("total", 0):
                    break
                start_at += len(issues)
        except Exception as e:
            logger.error("Failed to refresh sprint %d: %s", sprint_id, e)

    return json.dumps({"refreshed": len(refreshed), "keys": refreshed})


async def handle_cache_stats(args: dict) -> str:
    """Cache statistics."""
    stats = _require_cache().get_stats()
    if embeddings:
        stats["embeddings_count"] = embeddings.count()
        stats["embeddings_available"] = embeddings.available
    return json.dumps(stats, ensure_ascii=False)


async def handle_cache_invalidate(args: dict) -> str:
    """Cache invalidation with optional auto_refresh (P1-G)."""
    c = _require_cache()
    auto_refresh = args.get("auto_refresh", False)

    if args.get("all"):
        if not args.get("confirm"):
            return json.dumps({"error": "Set confirm=true to invalidate entire cache"})
        c.invalidate_all()
        return json.dumps({"invalidated": "all"})

    issue_key = args.get("issue_key")
    if issue_key:
        # M3: Validate key format — prevents spurious upstream calls on garbage input
        try:
            issue_key = _validate_issue_key(issue_key)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        removed = c.invalidate_issue(issue_key)
        if embeddings:
            embeddings.remove_embedding(issue_key)

        # P1-G: Auto-refresh after invalidation
        if auto_refresh and jira_api:
            try:
                issue = _timed_upstream(
                    f"auto_refresh({issue_key})",
                    jira_api.get_issue,
                    issue_key,
                )
                c.put_issue(issue_key, issue)
                # C4: Run CPU-bound model inference off the event loop to avoid blocking
                if embeddings and embeddings.available:
                    await asyncio.to_thread(embeddings.store_embedding, issue_key, _embedding_text(issue))
                # M9: strip_noise on auto_refresh response
                clean_issue = strip_noise(issue)
                return json.dumps(
                    {
                        "invalidated": issue_key,
                        "found": removed,
                        "auto_refreshed": True,
                        "issue": clean_issue,
                    }
                )
            except Exception as e:
                logger.error("Auto-refresh failed for %s: %s", issue_key, e)
                return json.dumps(
                    {
                        "invalidated": issue_key,
                        "found": removed,
                        "auto_refreshed": False,
                        "auto_refresh_error": str(e),
                    }
                )

        return json.dumps({"invalidated": issue_key, "found": removed})

    sprint_id = args.get("sprint_id")
    if sprint_id:
        count = c.invalidate_sprint(sprint_id)
        return json.dumps({"invalidated_sprint": sprint_id, "issues_removed": count})

    return json.dumps({"error": "Specify issue_key, sprint_id, or all=true"})


# --- Argument coercion (Claude sends strings for int/bool/number) ---

# Build schema lookup: tool_name -> {param_name: type_spec}
_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {}
for _t in TOOLS:
    props = _t.inputSchema.get("properties", {})
    _TOOL_SCHEMAS[_t.name] = {k: v.get("type") for k, v in props.items()}


def _coerce_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Coerce string arguments to their schema-declared types."""
    schema = _TOOL_SCHEMAS.get(name)
    if not schema:
        return args

    coerced = dict(args)
    # M6: Snapshot items before iterating — mutating a dict during iteration is
    # safe on CPython but undefined per spec (would raise on PyPy/alternate runtimes)
    for key, value in list(coerced.items()):
        if not isinstance(value, str):
            continue
        expected = schema.get(key)
        # Handle union types like ["integer", "string"]
        if isinstance(expected, list):
            if "integer" in expected:
                expected = "integer"
            elif "number" in expected:
                expected = "number"
            else:
                continue
        try:
            if expected == "integer":
                coerced[key] = int(value)
            elif expected == "number":
                coerced[key] = float(value)
            elif expected == "boolean":
                coerced[key] = value.lower() in ("true", "1", "yes")
            elif expected == "array":
                # ARRAY-COERCE: Handle JSON-encoded array strings (e.g. "[\"BEP-1\",\"BEP-2\"]")
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    coerced[key] = parsed
        except (ValueError, AttributeError, json.JSONDecodeError):
            pass  # Leave as-is if conversion fails
    return coerced


# --- Handler dispatch ---

HANDLERS = {
    "cache_get_issue": handle_cache_get_issue,
    "cache_get_issues": handle_cache_get_issues,
    "cache_search": handle_cache_search,
    "cache_sprint_issues": handle_cache_sprint_issues,
    "cache_text_search": handle_cache_text_search,
    "cache_similar_issues": handle_cache_similar_issues,
    "cache_refresh": handle_cache_refresh,
    "cache_stats": handle_cache_stats,
    "cache_invalidate": handle_cache_invalidate,
}


async def main() -> None:  # pragma: no cover
    """Run MCP server over stdio."""
    _init()

    server = Server("jira-cache-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        handler = HANDLERS.get(name)
        if not handler:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        try:
            arguments = _coerce_args(name, arguments)
            result = await handler(arguments)

            # P2-A: Always apply L1 strip on responses (noise already stripped at
            # storage, but upstream responses in auto_refresh may still have noise)
            if len(result) > MAX_RESPONSE_CHARS:
                # Level 1: Strip Jira metadata noise
                result = _strip_response_noise(result)
                logger.info("L1 strip: %d chars for %s", len(result), name)

            if len(result) > MAX_RESPONSE_CHARS:
                # Level 2: Paginate (return subset with has_more)
                logger.warning("L2 paginate: %d chars for %s", len(result), name)
                result = _paginate_response(result, name)

            if len(result) > MAX_RESPONSE_CHARS:
                # Level 3: Compact (replace issues with minimal summaries)
                logger.warning("L3 compact: %d chars for %s", len(result), name)
                result = _compact_response(result)

            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.exception("Tool %s failed", name)
            # Sanitize: only expose exception type and first 200 chars
            safe_msg = f"{type(e).__name__}: {str(e)[:200]}"
            return [TextContent(type="text", text=json.dumps({"error": safe_msg}))]

    logger.info("Starting jira-cache-server (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
