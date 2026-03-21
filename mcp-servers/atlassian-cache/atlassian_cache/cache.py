"""SQLite-based cache for Jira + Confluence data with FTS5 full-text search.

Provides structured caching with TTL expiration, full-text search on
issue summaries/descriptions, and ADF text extraction for indexing.

Usage:
    from atlassian_cache.cache import AtlassianCache

    cache = AtlassianCache()  # Uses ~/.cache/atlassian-pm/atlassian.db
    cache.put_issue("{{PROJECT_KEY}}-123", issue_data)
    cached = cache.get_issue("{{PROJECT_KEY}}-123", max_age_hours=24)
    results = cache.text_search("coupon payment", limit=10)
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from atlassian_cache.migrations import SCHEMA_VERSION, migrate

logger = logging.getLogger(__name__)

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
# S2: Resolve path to prevent traversal attacks via malformed CLAUDE_PLUGIN_DATA
DEFAULT_DB_PATH = (
    Path(os.path.abspath(_plugin_data)) if _plugin_data else Path.home() / ".cache" / "atlassian-pm"
) / "atlassian.db"

# Current schema version — re-exported from migrations for backwards compatibility
# SCHEMA_VERSION is imported above from atlassian_cache.migrations

# H3: Whitelist of allowed FTS5 operators (everything else stripped)
_FTS5_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9\u0E00-\u0E7F\s]")  # Keep alphanumeric + Thai + spaces

# M7: Maximum ADF recursion depth to prevent stack overflow
MAX_ADF_DEPTH = 50

# C4: Maximum DB size in MB (warn if exceeded)
MAX_DB_SIZE_MB = int(os.environ.get("ATLASSIAN_CACHE_MAX_DB_MB", "500"))

# NOTE: This FTS schema is only applied on fresh v1 databases. For databases
# that have gone through v5 migration, issues_fts is recreated by the migration
# with the porter tokenizer — these statements are no-ops on v5+ databases.
FTS_SCHEMA_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING fts5(
    issue_key UNINDEXED,
    summary,
    description_text,
    content=issues,
    content_rowid=rowid,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS issues_fts_insert AFTER INSERT ON issues BEGIN
    INSERT INTO issues_fts(rowid, issue_key, summary, description_text)
    VALUES (new.rowid, new.issue_key, new.summary, new.description_text);
END;

CREATE TRIGGER IF NOT EXISTS issues_fts_delete AFTER DELETE ON issues BEGIN
    INSERT INTO issues_fts(issues_fts, rowid, issue_key, summary, description_text)
    VALUES ('delete', old.rowid, old.issue_key, old.summary, old.description_text);
END;

CREATE TRIGGER IF NOT EXISTS issues_fts_update AFTER UPDATE ON issues BEGIN
    INSERT INTO issues_fts(issues_fts, rowid, issue_key, summary, description_text)
    VALUES ('delete', old.rowid, old.issue_key, old.summary, old.description_text);
    INSERT INTO issues_fts(rowid, issue_key, summary, description_text)
    VALUES (new.rowid, new.issue_key, new.summary, new.description_text);
END;
"""


# --- P2-A: Noise stripping at storage time ---

_NOISE_FIELDS = frozenset(
    {
        "self",  # REST API URL on every object
        "avatarUrls",  # 4 avatar size URLs per user
        "accountId",  # Internal Jira account ID
        "accountType",  # "atlassian" etc
        "emailAddress",  # Privacy; use displayName instead
        "timeZone",  # User timezone
        "active",  # User active status
        "iconUrl",  # Status/priority icon URLs
        "statusCategory",  # Redundant (use status.name)
        "expand",  # Jira API metadata
        "hierarchyLevel",  # Redundant issuetype metadata
        "subtask",  # Redundant boolean (use issuetype)
        "entityId",  # Internal entity ID
        "scope",  # Project scope details
    }
)


def strip_noise(obj: Any) -> Any:
    """Recursively strip noise fields from Jira response objects.

    Module-level function so server.py can also call it directly.
    """
    if isinstance(obj, dict):
        return {k: strip_noise(v) for k, v in obj.items() if k not in _NOISE_FIELDS}
    if isinstance(obj, list):
        return [strip_noise(item) for item in obj]
    return obj


def extract_adf_text(adf: Any) -> str | None:
    """Extract plain text from ADF (Atlassian Document Format) JSON.

    Recursively walks the ADF tree, collecting text from text nodes.
    M7: Limited to MAX_ADF_DEPTH to prevent stack overflow on malicious input.

    Args:
        adf: ADF document (dict) or None

    Returns:
        Concatenated text content, or None if no text found.
    """
    if not adf or not isinstance(adf, dict):
        return None

    parts: list[str] = []

    def walk(node: Any, depth: int = 0) -> None:
        if depth > MAX_ADF_DEPTH:  # pragma: no cover — defensive depth limit
            return
        if isinstance(node, dict):
            if node.get("type") == "text" and "text" in node:
                parts.append(node["text"])
            for key in ("content",):
                if key in node and isinstance(node[key], list):
                    for child in node[key]:
                        walk(child, depth + 1)
        elif isinstance(node, list):  # pragma: no cover — defensive
            for item in node:
                walk(item, depth + 1)

    walk(adf)
    text = " ".join(parts).strip()
    return text if text else None


def _extract_field(data: dict, *path: str, default: Any = None) -> Any:
    """Safely extract a nested field from issue data."""
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


# H7: TTL constants with env var overrides
_DEFAULT_TTL_HOURS = float(os.environ.get("ATLASSIAN_CACHE_DEFAULT_TTL_HOURS", "24"))
_DONE_TTL_HOURS = float(os.environ.get("ATLASSIAN_CACHE_DONE_TTL_HOURS", "168"))
_ACTIVE_TTL_HOURS = float(os.environ.get("ATLASSIAN_CACHE_ACTIVE_TTL_HOURS", "6"))

STATUS_TTL = {
    "Done": _DONE_TTL_HOURS,
    "Closed": _DONE_TTL_HOURS,
    "Won't Do": _DONE_TTL_HOURS,
    "In Progress": _ACTIVE_TTL_HOURS,
    "In Review": _ACTIVE_TTL_HOURS,
    "TO FIX": _ACTIVE_TTL_HOURS,
    "WAITING TO TEST": _ACTIVE_TTL_HOURS,
}
DEFAULT_TTL = _DEFAULT_TTL_HOURS

# --- P1-E: Stale data purge thresholds (with env overrides) ---
PURGE_ISSUES_DAYS = int(os.environ.get("ATLASSIAN_CACHE_PURGE_ISSUES_DAYS", "7"))
PURGE_SEARCHES_HOURS = int(os.environ.get("ATLASSIAN_CACHE_PURGE_SEARCHES_HOURS", "24"))


class AtlassianCache:
    """SQLite cache for Jira issues with FTS5 full-text search.

    Attributes:
        db_path: Path to SQLite database file.
        conn: SQLite connection.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        # Apply PRAGMAs before any migration — WAL must be set first
        self.conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA cache_size=-65536;        -- 64 MB in kibibytes (negative = kB)
            PRAGMA mmap_size=268435456;      -- 256 MB memory-mapped I/O
            PRAGMA temp_store=MEMORY;
            PRAGMA foreign_keys=ON;
        """)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        # L2: Separate lock for stat buffer (avoid contention with DB writes)
        self._stat_lock = threading.Lock()
        # P1-B: In-memory stat buffer (flush every N calls or on get_stats)
        self._stat_buffer: dict[str, int] = {"hits": 0, "misses": 0}
        self._stat_flush_threshold = int(os.environ.get("ATLASSIAN_CACHE_STAT_FLUSH_THRESHOLD", "20"))
        self._stat_buffer_count = 0
        self._last_purge_ts: float = 0.0  # guard: skip purge if ran recently
        self._init_schema()
        self._apply_pragmas()
        self._purge_stale()
        self._check_db_size()
        logger.debug("AtlassianCache initialized at %s", self.db_path)

    # --- P0: Migration system ---

    def _get_schema_version(self) -> int:
        """Get current schema version from PRAGMA user_version."""
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def _init_schema(self) -> None:
        """Create tables and run migrations via migrations.migrate()."""
        migrate(self.conn)

        # FTS5 setup (idempotent)
        try:
            self.conn.executescript(FTS_SCHEMA_SQL)
        except sqlite3.OperationalError as e:  # pragma: no cover — FTS5 IF NOT EXISTS
            if "already exists" not in str(e):
                logger.warning("FTS5 setup warning: %s", e)
        self.conn.commit()

    # --- P2-C: SQLite PRAGMA tuning ---

    def _apply_pragmas(self) -> None:
        """Apply additional session-level PRAGMAs (WAL + perf PRAGMAs already set at open time)."""
        self.conn.execute("PRAGMA busy_timeout = 5000")  # Wait 5s on lock contention
        self.conn.execute("PRAGMA wal_autocheckpoint = 100")  # Checkpoint every 100 pages

    # --- Helpers ---

    @staticmethod
    def _extract_sprint_id(fields: dict) -> int | None:
        """Extract sprint_id from custom field (can be list or dict)."""
        sprint_data = fields.get("customfield_10020")
        if isinstance(sprint_data, list) and sprint_data:
            first = sprint_data[0]
            return first.get("id") if isinstance(first, dict) else first
        if isinstance(sprint_data, dict):
            return sprint_data.get("id")
        return None

    # --- Issue Operations ---

    @staticmethod
    def _parse_cached_at(value: str) -> datetime:
        """Parse cached_at ISO string; treat naive timestamps as UTC for backwards compat."""
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def get_issue(self, issue_key: str, max_age_hours: float = 24.0) -> dict | None:
        """Get cached issue if fresh enough.

        Args:
            issue_key: Jira issue key (e.g., '{{PROJECT_KEY}}-123')
            max_age_hours: Maximum age in hours before considered stale

        Returns:
            Full issue JSON data, or None if not cached or stale.
        """
        row = self.conn.execute(
            "SELECT data, cached_at FROM issues WHERE issue_key = ?",
            (issue_key,),
        ).fetchone()

        if not row:
            self._incr_stat("misses")
            return None

        cached_at = self._parse_cached_at(row["cached_at"])
        if datetime.now(tz=timezone.utc) - cached_at > timedelta(hours=max_age_hours):
            self._incr_stat("misses")
            return None

        # P1-B: No more accessed_at UPDATE + COMMIT on read path
        self._incr_stat("hits")
        return json.loads(row["data"])

    def get_issue_stale(self, issue_key: str) -> dict | None:
        """Get cached issue regardless of age (for stale fallback).

        Returns:
            Full issue JSON data, or None if not in cache at all.
        """
        row = self.conn.execute(
            "SELECT data FROM issues WHERE issue_key = ?",
            (issue_key,),
        ).fetchone()
        return json.loads(row["data"]) if row else None

    def put_issue(self, issue_key: str, data: dict) -> None:
        """Store issue in cache, updating FTS5 index automatically.

        Args:
            issue_key: Jira issue key
            data: Full issue JSON from Jira API
        """
        # P2-A: Strip noise BEFORE storing
        data = strip_noise(data)

        # T12: Embed cache timestamp metadata so callers can do lazy version-checks
        now_ts = time.time()
        now_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat()
        data = {**data, "_cached_at": now_ts, "_cached_at_iso": now_iso}

        fields = data.get("fields", {})
        description_text = extract_adf_text(fields.get("description"))
        sprint_id = self._extract_sprint_id(fields)

        # Extract FTS-searchable text fields (v5 columns)
        labels_raw = fields.get("labels", [])
        labels_text = " ".join(str(lb) for lb in labels_raw) if isinstance(labels_raw, list) else ""
        assignee_name = (fields.get("assignee") or {}).get("displayName", "")

        # Use the already-computed UTC timestamp — avoids a second time syscall
        with self._lock:
            self._put_issue_row(
                issue_key,
                fields,
                description_text,
                sprint_id,
                data,
                now_iso,
                labels_text=labels_text,
                assignee_name=assignee_name,
            )
            self.conn.commit()
        logger.debug("Cached issue %s", issue_key)

    def _put_issue_row(
        self,
        issue_key: str,
        fields: dict,
        description_text: str | None,
        sprint_id: int | None,
        data: dict,
        now: str,
        *,
        labels_text: str = "",
        assignee_name: str = "",
    ) -> None:
        """Insert/replace a single issue row WITHOUT commit (for batch use)."""
        self.conn.execute(
            """INSERT OR REPLACE INTO issues
            (issue_key, summary, status, assignee, issue_type, sprint_id,
             parent_key, priority, labels, start_date, due_date,
             description_text, data, cached_at, accessed_at,
             labels_text, assignee_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                issue_key,
                fields.get("summary", ""),
                _extract_field(fields, "status", "name"),
                _extract_field(fields, "assignee", "displayName"),
                _extract_field(fields, "issuetype", "name"),
                sprint_id,
                _extract_field(fields, "parent", "key"),
                _extract_field(fields, "priority", "name"),
                json.dumps(fields.get("labels", [])),
                fields.get("customfield_10015"),
                fields.get("duedate"),
                description_text,
                json.dumps(data),
                now,
                None,  # P1-B: Stop writing accessed_at
                labels_text,
                assignee_name,
            ),
        )

    def _prepare_issue_row_args(self, issue_data: dict, now: str) -> tuple | None:
        """Extract and prepare all field args for _put_issue_row from raw issue data.

        Returns None if issue_data has no key. Used by both put_issues_batch and put_search
        to avoid duplicating the field extraction logic.
        """
        key = issue_data.get("key")
        if not key:
            return None
        issue_data = strip_noise(issue_data)
        fields = issue_data.get("fields", {})
        description_text = extract_adf_text(fields.get("description"))
        sprint_id = self._extract_sprint_id(fields)
        labels_raw = fields.get("labels", [])
        labels_text = " ".join(str(lb) for lb in labels_raw) if isinstance(labels_raw, list) else ""
        assignee_name = (fields.get("assignee") or {}).get("displayName", "")
        return (key, fields, description_text, sprint_id, issue_data, now,
                labels_text, assignee_name)

    def put_issues_batch(self, issues: list[dict]) -> int:
        """Bulk insert issues in a single transaction.

        P1-A: Uses _put_issue_row (no commit) + single COMMIT at end.

        Args:
            issues: List of issue dicts from Jira API

        Returns:
            Number of issues cached.
        """
        count = 0
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._lock:
            for issue_data in issues:
                args = self._prepare_issue_row_args(issue_data, now)
                if args:
                    key, fields, desc, sprint_id, data, ts, lbl, asgn = args
                    self._put_issue_row(key, fields, desc, sprint_id, data, ts,
                                        labels_text=lbl, assignee_name=asgn)
                    count += 1

            if count > 0:
                self.conn.commit()
        logger.info("Batch cached %d issues (single commit)", count)
        return count

    # --- P1-F: Batch get issues ---

    def get_issues_batch(self, issue_keys: list[str], max_age_hours: float = 24.0) -> tuple[list[dict], list[str]]:
        """Get multiple cached issues in one query.

        Args:
            issue_keys: List of issue keys
            max_age_hours: Maximum age in hours

        Returns:
            Tuple of (found_issues, missing_keys).
            found_issues: list of full issue JSON dicts
            missing_keys: list of keys not in cache or stale
        """
        if not issue_keys:
            return [], []

        placeholders = ",".join("?" * len(issue_keys))
        rows = self.conn.execute(
            f"SELECT issue_key, data, cached_at FROM issues WHERE issue_key IN ({placeholders})",
            issue_keys,
        ).fetchall()

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age_hours)
        found = {}
        for row in rows:
            cached_at = self._parse_cached_at(row["cached_at"])
            if cached_at >= cutoff:
                found[row["issue_key"]] = json.loads(row["data"])

        # Preserve order, track misses (batch stat increment)
        found_issues = []
        missing_keys = []
        hit_count = 0
        miss_count = 0
        for key in issue_keys:
            if key in found:
                found_issues.append(found[key])
                hit_count += 1
            else:
                missing_keys.append(key)
                miss_count += 1

        # L2: Single batch increment with _stat_lock (avoids mid-batch flush)
        with self._stat_lock:
            self._stat_buffer["hits"] += hit_count
            self._stat_buffer["misses"] += miss_count
            self._stat_buffer_count += hit_count + miss_count
            should_flush = self._stat_buffer_count >= self._stat_flush_threshold
        if should_flush:
            self._flush_stats()

        return found_issues, missing_keys

    # --- Sprint Operations ---

    def get_sprint(self, sprint_id: int, max_age_hours: float = 4.0) -> dict | None:
        """Get cached sprint metadata."""
        row = self.conn.execute(
            "SELECT data, cached_at FROM sprints WHERE sprint_id = ?",
            (sprint_id,),
        ).fetchone()

        if not row:
            return None

        cached_at = datetime.fromisoformat(row["cached_at"])
        if datetime.now() - cached_at > timedelta(hours=max_age_hours):
            return None

        return json.loads(row["data"])

    def put_sprint(self, sprint_id: int, data: dict) -> None:
        """Store sprint metadata in cache."""
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO sprints
                (sprint_id, name, state, start_date, end_date, goal, data, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sprint_id,
                    data.get("name", ""),
                    data.get("state"),
                    data.get("startDate"),
                    data.get("endDate"),
                    data.get("goal"),
                    json.dumps(data),
                    datetime.now().isoformat(),
                ),
            )
            self.conn.commit()

    # --- Search Cache ---

    def get_search(self, jql: str, fields: str, limit: int, max_age_hours: float = 2.0) -> dict | None:
        """Get cached search results."""
        cache_key = self._search_key(jql, fields, limit)
        row = self.conn.execute(
            "SELECT data, cached_at FROM searches WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()

        if not row:
            return None

        cached_at = self._parse_cached_at(row["cached_at"])
        if datetime.now(tz=timezone.utc) - cached_at > timedelta(hours=max_age_hours):
            return None

        self._incr_stat("hits")
        return json.loads(row["data"])

    def put_search(
        self,
        jql: str,
        fields: str,
        limit: int,
        data: dict,
        sprint_id: int | None = None,
    ) -> None:
        """Store search results and cache individual issues.

        M3: Optional sprint_id for sprint-specific search cache entries.
        H8: Single transaction for search + issues batch.
        """
        cache_key = self._search_key(jql, fields, limit)
        issues = data.get("issues", [])
        result_keys = [i.get("key", "") for i in issues]
        now = datetime.now(tz=timezone.utc).isoformat()

        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO searches
                (cache_key, jql, fields, result_keys, total, data, cached_at, sprint_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cache_key,
                    jql,
                    fields,
                    json.dumps(result_keys),
                    data.get("total", len(issues)),
                    json.dumps(data),
                    now,
                    sprint_id,
                ),
            )
            # H8: Batch insert issues in same transaction using shared _put_issue_row
            for issue_data in issues:
                args = self._prepare_issue_row_args(issue_data, now)
                if args:
                    key, flds, desc, sprint_id, data, ts, lbl, asgn = args
                    self._put_issue_row(key, flds, desc, sprint_id, data, ts,
                                        labels_text=lbl, assignee_name=asgn)
            self.conn.commit()
        logger.debug("Cached search + %d issues (single transaction)", len(issues))

    # --- Full-Text Search ---

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """H3: Whitelist-based FTS5 query sanitization.

        Only keeps alphanumeric characters (Latin + Thai) and spaces.
        Strips ALL special characters to prevent FTS5 injection
        (column filters, operators, boolean syntax abuse).
        """
        # Strip everything except alphanumeric + Thai + whitespace
        sanitized = _FTS5_ALLOWED_RE.sub(" ", query)
        # Collapse whitespace
        return " ".join(sanitized.split()).strip()

    def text_search(self, query: str, limit: int = 10) -> list[dict]:
        """FTS5 keyword search on cached issues.

        Args:
            query: Search query (supports FTS5 syntax like "coupon AND payment")
            limit: Maximum results

        Returns:
            List of matching issue data dicts, or empty list on FTS5 syntax error.
        """
        sanitized = self._sanitize_fts_query(query)
        if not sanitized:
            return []

        try:
            rows = self.conn.execute(
                """SELECT i.data FROM issues i
                JOIN issues_fts fts ON i.rowid = fts.rowid
                WHERE issues_fts MATCH ?
                ORDER BY rank
                LIMIT ?""",
                (sanitized, limit),
            ).fetchall()
            return [json.loads(row["data"]) for row in rows]
        except sqlite3.OperationalError as e:
            logger.warning("FTS5 query error for '%s': %s", query[:50], e)
            return []

    # --- Invalidation ---

    def invalidate_issue(self, issue_key: str) -> bool:
        """Remove an issue from cache."""
        with self._lock:
            cursor = self.conn.execute("DELETE FROM issues WHERE issue_key = ?", (issue_key,))
            self.conn.commit()
        return cursor.rowcount > 0

    def invalidate_sprint(self, sprint_id: int) -> int:
        """Remove all issues for a sprint, related searches, and the sprint itself."""
        with self._lock:
            cursor = self.conn.execute("DELETE FROM issues WHERE sprint_id = ?", (sprint_id,))
            # M3: Use indexed sprint_id column (fast) for rows stored after v3 migration
            self.conn.execute("DELETE FROM searches WHERE sprint_id = ?", (sprint_id,))
            # Legacy fallback: rows without sprint_id set (pre-v3 or missing put_search sprint_id arg)
            self.conn.execute(
                "DELETE FROM searches WHERE sprint_id IS NULL AND jql LIKE ?",
                (f"%sprint = {sprint_id}%",),
            )
            self.conn.execute("DELETE FROM sprints WHERE sprint_id = ?", (sprint_id,))
            self.conn.commit()
        return cursor.rowcount

    def invalidate_all(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self.conn.execute("DELETE FROM issues")
            self.conn.execute("DELETE FROM sprints")
            self.conn.execute("DELETE FROM searches")
            self.conn.commit()
        logger.info("Cache cleared")

    # --- P1-E: Stale data purge ---

    _PURGE_MIN_INTERVAL_S = 3600  # Skip purge if ran less than 1h ago

    def _purge_stale(self) -> dict[str, int]:
        """Purge stale issues (>7d) and searches (>24h) on startup.

        Guarded by _last_purge_ts to avoid expensive DELETE scans on every
        process restart (MCP servers restart frequently).
        """
        now_ts = time.time()
        if now_ts - self._last_purge_ts < self._PURGE_MIN_INTERVAL_S:
            return {"purged_issues": 0, "purged_searches": 0}
        now = datetime.now()
        issue_cutoff = (now - timedelta(days=PURGE_ISSUES_DAYS)).isoformat()
        search_cutoff = (now - timedelta(hours=PURGE_SEARCHES_HOURS)).isoformat()

        with self._lock:
            c1 = self.conn.execute("DELETE FROM issues WHERE cached_at < ?", (issue_cutoff,))
            c2 = self.conn.execute("DELETE FROM searches WHERE cached_at < ?", (search_cutoff,))
            purged_issues = c1.rowcount
            purged_searches = c2.rowcount

            if purged_issues > 0 or purged_searches > 0:
                # Update purge counters
                self.conn.execute(
                    "UPDATE cache_stats SET value = value + ? WHERE key = 'purged_issues'",
                    (purged_issues,),
                )
                self.conn.execute(
                    "UPDATE cache_stats SET value = value + ? WHERE key = 'purged_searches'",
                    (purged_searches,),
                )
                self.conn.commit()
                logger.info(
                    "Purged stale data: %d issues (>%dd), %d searches (>%dh)",
                    purged_issues,
                    PURGE_ISSUES_DAYS,
                    purged_searches,
                    PURGE_SEARCHES_HOURS,
                )

        self._last_purge_ts = now_ts
        return {"purged_issues": purged_issues, "purged_searches": purged_searches}

    def purge_stale(self) -> dict[str, int]:
        """Public interface for stale data purge. Always runs (bypasses startup guard)."""
        self._last_purge_ts = 0.0  # Reset guard so _purge_stale always runs
        return self._purge_stale()

    # --- Statistics ---

    def get_stats(self) -> dict:
        """Cache statistics: counts, size, hit rate."""
        # Flush stat buffer before reporting
        self._flush_stats()

        # P-PERF: Single query for all table counts + issue date range (5 queries → 1)
        row = self.conn.execute(
            """SELECT
                (SELECT COUNT(*) FROM issues),
                (SELECT COUNT(*) FROM sprints),
                (SELECT COUNT(*) FROM searches),
                (SELECT MIN(cached_at) FROM issues),
                (SELECT MAX(cached_at) FROM issues)"""
        ).fetchone()
        issue_count, sprint_count, search_count, oldest, newest = row

        # P-PERF: Batch stat reads — 2 DB round-trips instead of 4
        stat_rows = {
            r["key"]: r["value"]
            for r in self.conn.execute(
                "SELECT key, value FROM cache_stats WHERE key IN ('hits','misses','purged_issues','purged_searches')"
            ).fetchall()
        }
        with self._stat_lock:
            buffered = dict(self._stat_buffer)
        hits = stat_rows.get("hits", 0) + buffered.get("hits", 0)
        misses = stat_rows.get("misses", 0) + buffered.get("misses", 0)
        purged_issues = stat_rows.get("purged_issues", 0)
        purged_searches = stat_rows.get("purged_searches", 0)
        total = hits + misses

        db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

        return {
            "issues_cached": issue_count,
            "sprints_cached": sprint_count,
            "searches_cached": search_count,
            "hits": hits,
            "misses": misses,
            "hit_rate": f"{hits / total * 100:.1f}%" if total > 0 else "N/A",
            "purged_issues": purged_issues,
            "purged_searches": purged_searches,
            "db_size_mb": round(db_size_mb, 2),
            "oldest_entry": oldest,
            "newest_entry": newest,
            "schema_version": self._get_schema_version(),
            "embedding_available": False,  # server.py injects the real value
        }

    def vacuum(self) -> None:
        """Optimize database (reclaim space)."""
        self.conn.execute("VACUUM")
        self.conn.execute("ANALYZE")

    # --- Internal ---

    def _search_key(self, jql: str, fields: str, limit: int) -> str:
        """P1-D: Normalized search key to avoid duplicate cache entries.

        Uses MD5 (not SHA256) — this is a cache key, not a security hash.
        MD5 is ~2x faster and produces a shorter key (32 vs 64 hex chars).
        """
        # Normalize JQL: collapse whitespace, lowercase
        jql_norm = " ".join(jql.lower().split())
        # Normalize fields: sort, strip whitespace
        fields_norm = ",".join(sorted(f.strip() for f in fields.split(",")))
        raw = f"{jql_norm}|{fields_norm}|{limit}"
        return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324

    # --- P1-B: Deferred stat counting ---

    def _incr_stat(self, key: str) -> None:
        """Buffer stat increments in memory; flush periodically.

        L2: Uses _stat_lock for thread-safe buffer access.
        """
        with self._stat_lock:
            self._stat_buffer[key] = self._stat_buffer.get(key, 0) + 1
            self._stat_buffer_count += 1
            should_flush = self._stat_buffer_count >= self._stat_flush_threshold
        if should_flush:
            self._flush_stats()

    def _flush_stats(self) -> None:
        """Flush buffered stats to SQLite.

        L2: Uses _stat_lock (not _lock) to avoid contention with DB writes.
        C1: Guard check moved inside lock to eliminate TOCTOU race.
        """
        with self._stat_lock:
            if self._stat_buffer_count == 0:
                return
            snapshot = {k: v for k, v in self._stat_buffer.items() if v > 0}
            self._stat_buffer = {k: 0 for k in self._stat_buffer}
            self._stat_buffer_count = 0
        if snapshot:
            with self._lock:
                for key, val in snapshot.items():
                    self.conn.execute(
                        "UPDATE cache_stats SET value = value + ? WHERE key = ?",
                        (val, key),
                    )
                self.conn.commit()

    def _get_stat(self, key: str) -> int:
        """Get stat value from DB plus unflushed buffer for accurate real-time reads."""
        row = self.conn.execute("SELECT value FROM cache_stats WHERE key = ?", (key,)).fetchone()
        db_val = row[0] if row else 0
        # C2: Lock buffer read to avoid race with concurrent _incr_stat
        with self._stat_lock:
            buffered = self._stat_buffer.get(key, 0)
        return db_val + buffered

    def get_adaptive_ttl(self, issue_key: str) -> float:
        """Get TTL based on issue status. Done=7d, Active=6h, else=24h."""
        row = self.conn.execute("SELECT status FROM issues WHERE issue_key = ?", (issue_key,)).fetchone()
        if not row:
            return DEFAULT_TTL
        return STATUS_TTL.get(row["status"], DEFAULT_TTL)

    # --- C4: DB size monitoring ---

    def _check_db_size(self) -> None:
        """Warn if database exceeds MAX_DB_SIZE_MB."""
        if not self.db_path.exists():
            return
        size_mb = self.db_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_DB_SIZE_MB:
            logger.warning(
                "DB size %.1f MB exceeds limit %d MB — consider running vacuum() or purge_stale()",
                size_mb,
                MAX_DB_SIZE_MB,
            )

    def get_all_issues(self) -> list[dict]:
        """Return minimal issue dicts for reindex (key + fields.summary/description only).

        Avoids loading full JSON blobs — reindex only needs summary and description for
        embedding_text(). Returns synthetic dicts compatible with embedding_text().
        """
        rows = self.conn.execute(
            "SELECT issue_key, summary, description_text FROM issues"
        ).fetchall()
        return [
            {
                "key": r["issue_key"],
                "fields": {
                    "summary": r["summary"] or "",
                    "description": r["description_text"] or "",
                },
            }
            for r in rows
        ]

    def get_all_sprints(self) -> list[dict]:
        """Return all cached sprints that have a goal (for reindex)."""
        rows = self.conn.execute(
            "SELECT sprint_id, name, goal FROM sprints WHERE goal IS NOT NULL AND goal != ''"
        ).fetchall()
        return [{"sprint_id": r["sprint_id"], "name": r["name"], "goal": r["goal"]} for r in rows]

    def close(self) -> None:
        """Close database connection (flush stats first)."""
        self._flush_stats()
        self.conn.close()
