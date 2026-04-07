"""Schema version management for atlassian-cache SQLite database.

All DDL lives here. cache.py and confluence_cache.py delegate to migrate().
"""
import logging
import sqlite3
from typing import Callable, Union

logger = logging.getLogger(__name__)

# Increment whenever a new migration step is added
# SCHEMA_VERSION is defined after _MIGRATIONS dict (near bottom of module)

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

# M2: Migration to v2: drop accessed_at column (P1-B), add purge stats
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

# M4: Migration to v4: add Confluence tables
_MIGRATION_V4 = """
CREATE TABLE IF NOT EXISTS confluence_pages (
    page_id     TEXT PRIMARY KEY,
    space_key   TEXT NOT NULL,
    title       TEXT NOT NULL,
    body_md     TEXT,
    version_num INTEGER NOT NULL DEFAULT 0,
    version_when TEXT,
    labels      TEXT,
    author      TEXT,
    cached_at   REAL NOT NULL,
    url         TEXT
);

CREATE TABLE IF NOT EXISTS confluence_links (
    from_page_id TEXT NOT NULL,
    to_page_id   TEXT NOT NULL,
    link_type    TEXT DEFAULT 'child',
    PRIMARY KEY (from_page_id, to_page_id)
);

CREATE TABLE IF NOT EXISTS confluence_searches (
    search_key  TEXT PRIMARY KEY,
    result_json TEXT NOT NULL,
    cached_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS confluence_sections (
    section_id   TEXT PRIMARY KEY,
    page_id      TEXT NOT NULL,
    heading      TEXT NOT NULL,
    body_md      TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    cached_at    REAL NOT NULL,
    FOREIGN KEY (page_id) REFERENCES confluence_pages(page_id)
);

CREATE TABLE IF NOT EXISTS confluence_sprint_links (
    page_id   TEXT NOT NULL,
    sprint_id INTEGER NOT NULL,
    PRIMARY KEY (page_id, sprint_id)
);

INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('confluence_hits', 0);
INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('confluence_misses', 0);
"""

# M5: Migration to v5: FTS5 porter tokenizer, labels_text/assignee_name columns, confluence_fts
# Uses a callable instead of raw SQL string because CREATE TRIGGER bodies contain
# internal semicolons that would break the simple split(";") approach used for v2-v4.
def _apply_migration_v5(conn: sqlite3.Connection) -> None:
    """Apply v5: porter tokenizer FTS, new columns, confluence_fts."""
    # Step 1: Add new columns (simple ALTER TABLE — safe with split approach)
    conn.execute("ALTER TABLE issues ADD COLUMN labels_text TEXT DEFAULT ''")
    conn.execute("ALTER TABLE issues ADD COLUMN assignee_name TEXT DEFAULT ''")

    # Step 2: Drop old FTS table and triggers
    conn.execute("DROP TABLE IF EXISTS issues_fts")
    conn.execute("DROP TRIGGER IF EXISTS issues_fts_insert")
    conn.execute("DROP TRIGGER IF EXISTS issues_fts_delete")
    conn.execute("DROP TRIGGER IF EXISTS issues_fts_update")

    # Step 3: Recreate FTS table with porter tokenizer + new columns
    conn.execute("""
        CREATE VIRTUAL TABLE issues_fts USING fts5(
            issue_key UNINDEXED,
            summary,
            description_text,
            labels_text,
            assignee_name,
            content=issues,
            content_rowid=rowid,
            tokenize='porter unicode61'
        )
    """)

    # Step 4: Recreate triggers for issues_fts
    conn.execute("""
        CREATE TRIGGER issues_fts_insert AFTER INSERT ON issues BEGIN
            INSERT INTO issues_fts(rowid, issue_key, summary, description_text, labels_text, assignee_name)
            VALUES (new.rowid, new.issue_key, new.summary, new.description_text,
                    COALESCE(new.labels_text, ''), COALESCE(new.assignee_name, ''));
        END
    """)
    conn.execute("""
        CREATE TRIGGER issues_fts_delete AFTER DELETE ON issues BEGIN
            INSERT INTO issues_fts(issues_fts, rowid, issue_key, summary, description_text, labels_text, assignee_name)
            VALUES ('delete', old.rowid, old.issue_key, old.summary, old.description_text,
                    COALESCE(old.labels_text, ''), COALESCE(old.assignee_name, ''));
        END
    """)
    conn.execute("""
        CREATE TRIGGER issues_fts_update AFTER UPDATE ON issues BEGIN
            INSERT INTO issues_fts(issues_fts, rowid, issue_key, summary, description_text, labels_text, assignee_name)
            VALUES ('delete', old.rowid, old.issue_key, old.summary, old.description_text,
                    COALESCE(old.labels_text, ''), COALESCE(old.assignee_name, ''));
            INSERT INTO issues_fts(rowid, issue_key, summary, description_text, labels_text, assignee_name)
            VALUES (new.rowid, new.issue_key, new.summary, new.description_text,
                    COALESCE(new.labels_text, ''), COALESCE(new.assignee_name, ''));
        END
    """)

    # Step 5: Create confluence_fts virtual table
    # content='' (contentless) because confluence_pages has body_md and labels,
    # not body_text and labels_text. Triggers transform the data manually on every
    # write, so SQLite never needs to read columns from the base table for FTS.
    # Using content=confluence_pages would cause 'rebuild' to fail at runtime.
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS confluence_fts USING fts5(
            page_id UNINDEXED,
            title,
            body_text,
            labels_text,
            content='',
            tokenize='porter unicode61'
        )
    """)

    # Step 6: Create triggers for confluence_fts
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS confluence_fts_insert AFTER INSERT ON confluence_pages BEGIN
            INSERT INTO confluence_fts(rowid, page_id, title, body_text, labels_text)
            VALUES (new.rowid, new.page_id, new.title,
                    COALESCE(SUBSTR(new.body_md, 1, 50000), ''),
                    COALESCE(new.labels, ''));
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS confluence_fts_delete AFTER DELETE ON confluence_pages BEGIN
            INSERT INTO confluence_fts(confluence_fts, rowid, page_id, title, body_text, labels_text)
            VALUES ('delete', old.rowid, old.page_id, old.title,
                    COALESCE(SUBSTR(old.body_md, 1, 50000), ''),
                    COALESCE(old.labels, ''));
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS confluence_fts_update AFTER UPDATE ON confluence_pages BEGIN
            INSERT INTO confluence_fts(confluence_fts, rowid, page_id, title, body_text, labels_text)
            VALUES ('delete', old.rowid, old.page_id, old.title,
                    COALESCE(SUBSTR(old.body_md, 1, 50000), ''),
                    COALESCE(old.labels, ''));
            INSERT INTO confluence_fts(rowid, page_id, title, body_text, labels_text)
            VALUES (new.rowid, new.page_id, new.title,
                    COALESCE(SUBSTR(new.body_md, 1, 50000), ''),
                    COALESCE(new.labels, ''));
        END
    """)


# M6: Migration to v6: index on confluence_sections.page_id + fix FTS truncation 50K→512K
def _apply_migration_v6(conn: sqlite3.Connection) -> None:
    """Apply v6: page_id index on confluence_sections, fix confluence_fts truncation."""
    # Step 1: Add missing index — was omitted from v4, causes full table scan per get_sections
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_confluence_sections_page ON confluence_sections(page_id)"
    )

    # Step 2: Fix FTS truncation mismatch — triggers cap at 50K but app allows 512K.
    # Drop and recreate all three confluence_fts triggers with the correct limit.
    conn.execute("DROP TRIGGER IF EXISTS confluence_fts_insert")
    conn.execute("DROP TRIGGER IF EXISTS confluence_fts_delete")
    conn.execute("DROP TRIGGER IF EXISTS confluence_fts_update")

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS confluence_fts_insert AFTER INSERT ON confluence_pages BEGIN
            INSERT INTO confluence_fts(rowid, page_id, title, body_text, labels_text)
            VALUES (new.rowid, new.page_id, new.title,
                    COALESCE(SUBSTR(new.body_md, 1, 512000), ''),
                    COALESCE(new.labels, ''));
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS confluence_fts_delete AFTER DELETE ON confluence_pages BEGIN
            INSERT INTO confluence_fts(confluence_fts, rowid, page_id, title, body_text, labels_text)
            VALUES ('delete', old.rowid, old.page_id, old.title,
                    COALESCE(SUBSTR(old.body_md, 1, 512000), ''),
                    COALESCE(old.labels, ''));
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS confluence_fts_update AFTER UPDATE ON confluence_pages BEGIN
            INSERT INTO confluence_fts(confluence_fts, rowid, page_id, title, body_text, labels_text)
            VALUES ('delete', old.rowid, old.page_id, old.title,
                    COALESCE(SUBSTR(old.body_md, 1, 512000), ''),
                    COALESCE(old.labels, ''));
            INSERT INTO confluence_fts(rowid, page_id, title, body_text, labels_text)
            VALUES (new.rowid, new.page_id, new.title,
                    COALESCE(SUBSTR(new.body_md, 1, 512000), ''),
                    COALESCE(new.labels, ''));
        END
    """)


# M7: Migration to v7: token_metrics table for tracking token savings
_MIGRATION_V7 = """
CREATE TABLE IF NOT EXISTS token_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tool TEXT NOT NULL,
    operation TEXT NOT NULL,
    chars_before INTEGER DEFAULT 0,
    chars_after INTEGER DEFAULT 0,
    tokens_saved INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_token_metrics_timestamp ON token_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_token_metrics_tool ON token_metrics(tool);

INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('tokens_saved_total', 0);
"""

_MIGRATION_V8 = """
CREATE INDEX IF NOT EXISTS idx_confluence_links_to ON confluence_links(to_page_id);
CREATE INDEX IF NOT EXISTS idx_confluence_sprint_links_page ON confluence_sprint_links(page_id);
"""

_MIGRATIONS: dict[int, Union[str, Callable[[sqlite3.Connection], None]]] = {
    2: _MIGRATION_V2,
    3: _MIGRATION_V3,
    4: _MIGRATION_V4,
    5: _apply_migration_v5,
    6: _apply_migration_v6,
    7: _MIGRATION_V7,
    8: _MIGRATION_V8,
}
SCHEMA_VERSION = 8


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
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
        current = 1
        logger.info("migrations: initialized schema at v1")

    for version in range(current + 1, SCHEMA_VERSION + 1):
        migration = _MIGRATIONS.get(version)
        if migration is None:
            logger.warning("migrations: no migration defined for v%d", version)
            continue
        logger.info("migrations: applying v%d", version)
        # Each step in its own transaction so failure leaves DB at prior version
        conn.execute("BEGIN")
        try:
            if callable(migration):
                # Callable migration: receives conn, executes statements directly.
                # Used when SQL contains trigger bodies with internal semicolons
                # that would break simple split(";") parsing.
                migration(conn)
            else:
                for statement in migration.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        conn.execute(stmt)
            # PRAGMA user_version writes to the DB header outside the WAL journal —
            # it cannot be rolled back. Must stay AFTER all DML so that any DML
            # failure raises before this line, leaving user_version unchanged.
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
            logger.info("migrations: v%d applied", version)
        except sqlite3.OperationalError:
            conn.rollback()
            raise
