"""Schema version management for atlassian-cache SQLite database.

All DDL lives here. cache.py and confluence_cache.py delegate to migrate().
"""
import logging
import sqlite3

logger = logging.getLogger(__name__)

# Increment whenever a new migration step is added
SCHEMA_VERSION = 3  # Will become 4 and 5 in later tasks

# --- DDL ---

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS issues (
    issue_key TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    status TEXT,
    assignee TEXT,
    issue_type TEXT,
    sprint_id INTEGER,
    parent_key TEXT,
    priority TEXT,
    labels TEXT,
    start_date TEXT,
    due_date TEXT,
    description_text TEXT,
    data TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    accessed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_issues_sprint ON issues(sprint_id);
CREATE INDEX IF NOT EXISTS idx_issues_parent ON issues(parent_key);
CREATE INDEX IF NOT EXISTS idx_issues_cached ON issues(cached_at);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_assignee ON issues(assignee);

CREATE TABLE IF NOT EXISTS sprints (
    sprint_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT,
    start_date TEXT,
    end_date TEXT,
    goal TEXT,
    data TEXT NOT NULL,
    cached_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS searches (
    cache_key TEXT PRIMARY KEY,
    jql TEXT NOT NULL,
    fields TEXT NOT NULL,
    result_keys TEXT NOT NULL,
    total INTEGER,
    data TEXT NOT NULL,
    cached_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_searches_cached ON searches(cached_at);

CREATE TABLE IF NOT EXISTS cache_stats (
    key TEXT PRIMARY KEY,
    value INTEGER DEFAULT 0
);

INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('hits', 0);
INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('misses', 0);
"""

# Migration to v2: drop accessed_at column (P1-B), add purge stats
_MIGRATION_V2 = """
-- P1-B: accessed_at is unused (deferred stat counting replaces it)
-- SQLite doesn't support DROP COLUMN before 3.35 so we just leave it
-- but stop writing to it. New stat counters for purge tracking:
INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('purged_issues', 0);
INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('purged_searches', 0);
"""

# M3: Migration to v3: add sprint_id to searches table
_MIGRATION_V3 = """
ALTER TABLE searches ADD COLUMN sprint_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_searches_sprint ON searches(sprint_id);
"""

_MIGRATIONS: dict[int, str] = {
    2: _MIGRATION_V2,
    3: _MIGRATION_V3,
}


def migrate(conn: sqlite3.Connection) -> None:
    """Run all pending migrations in order.

    Reads PRAGMA user_version to determine current version,
    applies each missing step in a transaction, updates user_version.

    Raises:
        sqlite3.OperationalError: If a migration step fails (DB stays at prior version).
    """
    current = conn.execute("PRAGMA user_version").fetchone()[0]

    if current == 0:
        # Fresh database — apply full v1 schema
        conn.executescript(_SCHEMA_V1)
        conn.execute(f"PRAGMA user_version = 1")
        conn.commit()
        current = 1
        logger.info("migrations: initialized schema at v1")

    for version in range(current + 1, SCHEMA_VERSION + 1):
        sql = _MIGRATIONS.get(version)
        if sql is None:
            logger.warning("migrations: no migration defined for v%d", version)
            continue
        logger.info("migrations: applying v%d", version)
        # Each step in its own transaction so failure leaves DB at prior version
        conn.execute("BEGIN")
        try:
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
            logger.info("migrations: v%d applied", version)
        except sqlite3.OperationalError:
            conn.rollback()
            raise
