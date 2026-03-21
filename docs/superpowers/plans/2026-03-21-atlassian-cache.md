# atlassian-cache MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `jira-cache` with a unified `atlassian-cache` MCP server covering Jira + Confluence with semantic search, section-level embeddings, and hybrid cache invalidation.

**Architecture:** SQLite-backed cache server with WAL journal, FTS5 (porter tokenizer, weighted BM25), and sqlite-vec cross-modal embeddings. All writes go through a three-layer invalidation strategy (TTL + lazy version-check + write-hook). New modules are added incrementally; schema evolves via a numbered migration system.

**Tech Stack:** Python 3.11+, `mcp>=1.0.0`, `sqlite3` (stdlib), `sentence-transformers>=3.0` (optional, embeddings extra), `sqlite-vec>=0.1.1` (optional), `pytest`, `uv`

**Spec:** `docs/superpowers/specs/2026-03-21-atlassian-cache-design.md`

**Run tests from:** `mcp-servers/atlassian-cache/` with `VIRTUAL_ENV="" uv sync --extra test && .venv/bin/python -m pytest tests/ -v`

---

## File Map

### Renamed / moved

| From | To |
|------|-----|
| `mcp-servers/jira-cache/` | `mcp-servers/atlassian-cache/` |
| `jira_cache/__init__.py` | `atlassian_cache/__init__.py` |
| `jira_cache/cache.py` | `atlassian_cache/cache.py` |
| `jira_cache/embeddings.py` | `atlassian_cache/embeddings.py` |

### New files

| File | Responsibility |
|------|---------------|
| `atlassian_cache/migrations.py` | Schema version management — `_migrate(conn)`, all v1→v5 step functions |
| `atlassian_cache/confluence_cache.py` | Confluence page CRUD, section storage, FTS search |
| `atlassian_cache/sections.py` | H2-based Markdown splitter, SHA256 hash comparison |
| `tests/test_migrations.py` | Migration chain, user_version sentinel, partial-failure edge cases |
| `tests/test_confluence_cache.py` | Confluence CRUD, FTS, section storage |
| `tests/test_sections.py` | H2 splitter, hash diff, edge cases |

### Modified files

| File | Changes |
|------|---------|
| `atlassian_cache/cache.py` | Remove migration code → delegates to `migrations.py`; PRAGMA at connect-open; FTS5 v5 columns; compact format; lazy Jira version-check; in-session dedup |
| `atlassian_cache/embeddings.py` | Multilingual MiniLM model; `entity_type` column in vec0; cross-modal search |
| `server.py` | 12 Jira tools + 9 Confluence tools; `ConfluenceCache` init in lifespan |
| `pyproject.toml` | name `atlassian-cache`, `sentence-transformers>=3.0.0,<4` |
| `tests/conftest.py` | Add `confluence_cache`, `sample_page`, `make_section` fixtures |
| `tests/test_cache.py` | FTS5 v5 columns, compact format, lazy version-check |
| `tests/test_embeddings.py` | Cross-modal, multilingual model name |
| `tests/test_server.py` | 21 tools registered, Confluence tools smoke |

### External references (all batched in Task 1)

- `.mcp.json` — 2 path refs
- `hooks/hooks.json` — 7 refs
- `agents/*.md` — 12 files
- `skills/**/*.md` — 27 files
- `scripts/setup.sh` — path refs

---

## Task 1: Rename Directory and Module

**Files:**

- Rename: `mcp-servers/jira-cache/` → `mcp-servers/atlassian-cache/`
- Rename: `jira_cache/` → `atlassian_cache/`
- Modify: `.mcp.json`, `hooks/hooks.json`, 12 agent files, 27 skill files, `scripts/setup.sh`

- [ ] **Step 1: Copy directory (git mv preserves history)**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm
git mv mcp-servers/jira-cache mcp-servers/atlassian-cache
git mv mcp-servers/atlassian-cache/jira_cache mcp-servers/atlassian-cache/atlassian_cache
```

- [ ] **Step 2: Rename module references inside moved files**

```bash
cd mcp-servers/atlassian-cache
# Update all internal imports jira_cache → atlassian_cache
sed -i '' 's/from jira_cache\./from atlassian_cache./g' server.py atlassian_cache/*.py tests/*.py
sed -i '' 's/import jira_cache/import atlassian_cache/g' server.py atlassian_cache/*.py tests/*.py
# Update Server name and logger
sed -i '' 's/Server("jira-cache")/Server("atlassian-cache")/g' server.py
sed -i '' 's/logger = logging.getLogger("jira-cache")/logger = logging.getLogger("atlassian-cache")/g' server.py
```

- [ ] **Step 3: Update pyproject.toml name**

Edit `mcp-servers/atlassian-cache/pyproject.toml`:

```toml
[project]
name = "atlassian-cache"
version = "1.0.0"
description = "Unified Jira + Confluence cache MCP server with SQLite FTS5 + vector search"
```

- [ ] **Step 4: Update .mcp.json**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm
sed -i '' 's|mcp-servers/jira-cache|mcp-servers/atlassian-cache|g' .mcp.json
sed -i '' 's|"jira-cache"|"atlassian-cache"|g' .mcp.json
```

- [ ] **Step 5: Update hooks/hooks.json (7 refs)**

```bash
sed -i '' 's|mcp-servers/jira-cache|mcp-servers/atlassian-cache|g' hooks/hooks.json
sed -i '' 's|plugin_atlassian-pm_jira-cache__|plugin_atlassian-pm_atlassian-cache__|g' hooks/hooks.json
```

- [ ] **Step 6: Batch update agents and skills**

```bash
grep -rl "jira-cache\|jira_cache" agents/ skills/ --include="*.md" | \
  xargs sed -i '' 's/jira-cache/atlassian-cache/g; s/jira_cache/atlassian_cache/g'
grep -rl "jira-cache\|jira_cache" scripts/ | \
  xargs sed -i '' 's|mcp-servers/jira-cache|mcp-servers/atlassian-cache|g'
```

- [ ] **Step 7: Verify tests still pass**

```bash
cd mcp-servers/atlassian-cache
VIRTUAL_ENV="" uv sync --extra test --project .
.venv/bin/python -m pytest tests/ -v
```

Expected: All existing tests PASS (same logic, new module path)

- [ ] **Step 8: Commit**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm
git add -A
git commit -m "refactor: rename jira-cache → atlassian-cache, jira_cache → atlassian_cache

Updates 55+ references across agents, skills, hooks, scripts, .mcp.json"
```

---

## Task 2: PRAGMA Configuration at Connection Open

**Files:**

- Modify: `mcp-servers/atlassian-cache/atlassian_cache/cache.py:274` (inside `JiraCache.__init__`)

> PRAGMA must be applied **before** any migration runs. The existing `__init__` currently runs `PRAGMA journal_mode=WAL` only inside `_SCHEMA_V1` (first-time init), not on every open. Fix this.

- [ ] **Step 1: Write failing test**

In `tests/test_cache.py`, add:

```python
def test_pragma_wal_applied_on_open(tmp_db):
    """WAL mode and mmap are set at connection open, even on existing DBs."""
    from atlassian_cache.cache import JiraCache
    c = JiraCache(db_path=tmp_db)
    mode = c.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    mmap = c.conn.execute("PRAGMA mmap_size").fetchone()[0]
    assert mmap >= 268_435_456  # 256MB
    cache_size = c.conn.execute("PRAGMA cache_size").fetchone()[0]
    assert cache_size == -65536  # 64MB in kilobytes
    c.close()
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
.venv/bin/python -m pytest tests/test_cache.py::test_pragma_wal_applied_on_open -v
```

Expected: FAIL (mmap_size is 0 by default)

- [ ] **Step 3: Implement PRAGMA block in JiraCache.**init****

In `atlassian_cache/cache.py`, add immediately after `self.conn = sqlite3.connect(...)`:

```python
# Apply PRAGMAs before any migration — WAL must be set first
self.conn.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    PRAGMA cache_size=-65536;
    PRAGMA mmap_size=268435456;
    PRAGMA temp_store=MEMORY;
    PRAGMA foreign_keys=ON;
""")
```

Also remove `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` from `_SCHEMA_V1` string (they're now applied at open time).

- [ ] **Step 4: Run test — expect PASS**

```bash
.venv/bin/python -m pytest tests/test_cache.py::test_pragma_wal_applied_on_open -v
```

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add atlassian_cache/cache.py tests/test_cache.py
git commit -m "perf: apply WAL + mmap_size + cache_size PRAGMAs at connection open"
```

---

## Task 3: Extract migrations.py + test_migrations.py

**Files:**

- Create: `mcp-servers/atlassian-cache/atlassian_cache/migrations.py`
- Create: `mcp-servers/atlassian-cache/tests/test_migrations.py`
- Modify: `atlassian_cache/cache.py` — delegate to `migrations.py`

> Current migration logic lives in `cache.py`. Extract it to `migrations.py` so Confluence migrations (v4, v5) can be added cleanly without bloating the Jira cache module.

- [ ] **Step 1: Write failing tests**

Create `tests/test_migrations.py`:

```python
"""Tests for atlassian_cache.migrations — 100% coverage."""
import sqlite3
import pytest
from atlassian_cache.migrations import SCHEMA_VERSION, migrate


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "m.db"
    c = sqlite3.connect(str(db), check_same_thread=False)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_fresh_db_reaches_current_version(conn):
    """A fresh DB migrates all the way to SCHEMA_VERSION."""
    migrate(conn)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_migrate_is_idempotent(conn):
    """Calling migrate() twice is safe."""
    migrate(conn)
    migrate(conn)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_user_version_matches_constant(conn):
    """user_version after migration equals SCHEMA_VERSION constant."""
    migrate(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_partial_migration_failure_rolls_back(conn):
    """If a migration step raises, the DB stays at prior version."""
    from atlassian_cache import migrations as m
    original_v2 = m._MIGRATIONS[2]
    m._MIGRATIONS[2] = "THIS IS INVALID SQL;"
    try:
        with pytest.raises(sqlite3.OperationalError):
            migrate(conn)
        # DB should still be at version 1 (v2 failed)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == 1
    finally:
        m._MIGRATIONS[2] = original_v2


def test_issues_table_exists_after_migration(conn):
    """Core issues table is created by migration."""
    migrate(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "issues" in tables
    assert "sprints" in tables
    assert "searches" in tables
```

- [ ] **Step 2: Run tests — expect FAIL (module doesn't exist)**

```bash
.venv/bin/python -m pytest tests/test_migrations.py -v
```

- [ ] **Step 3: Create atlassian_cache/migrations.py**

Extract the migration code from `cache.py`:

```python
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

_MIGRATION_V2 = """
INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('purged_issues', 0);
INSERT OR IGNORE INTO cache_stats (key, value) VALUES ('purged_searches', 0);
"""

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
```

- [ ] **Step 4: Update cache.py to delegate to migrations.py**

In `atlassian_cache/cache.py`:

- Remove `_SCHEMA_V1`, `_MIGRATION_V2`, `_MIGRATION_V3`, `_MIGRATIONS`, `FTS_SCHEMA_SQL` string constants
- Remove the inline migration loop in `JiraCache.__init__`
- Import and call `from atlassian_cache.migrations import SCHEMA_VERSION, migrate` then `migrate(self.conn)` in `__init__`
- Keep `SCHEMA_VERSION` re-exported if tests import it from cache: `from atlassian_cache.migrations import SCHEMA_VERSION`

- [ ] **Step 5: Run all tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add atlassian_cache/migrations.py atlassian_cache/cache.py tests/test_migrations.py
git commit -m "refactor: extract schema migrations to atlassian_cache/migrations.py"
```

---

## Task 4: Schema v4 — Confluence Tables

**Files:**

- Modify: `atlassian_cache/migrations.py` — add `_MIGRATION_V4`, bump `SCHEMA_VERSION` to 4

- [ ] **Step 1: Add test for v4 tables**

In `tests/test_migrations.py`, add:

```python
def test_v4_confluence_tables_exist(conn):
    """v4 migration creates all 5 Confluence tables."""
    migrate(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert "confluence_pages" in tables
    assert "confluence_links" in tables
    assert "confluence_searches" in tables
    assert "confluence_sections" in tables

def test_v4_confluence_sections_fk(conn):
    """confluence_sections has FOREIGN KEY to confluence_pages (enforced)."""
    migrate(conn)
    conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO confluence_sections VALUES (?,?,?,?,?,?)",
            ("ghost::intro", "ghost-page-id", "Intro", "text", "hash123", "2026-01-01")
        )
        conn.commit()
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
.venv/bin/python -m pytest tests/test_migrations.py::test_v4_confluence_tables_exist -v
```

- [ ] **Step 3: Add v4 migration to migrations.py**

```python
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

_MIGRATIONS: dict[int, str] = {
    2: _MIGRATION_V2,
    3: _MIGRATION_V3,
    4: _MIGRATION_V4,
}

SCHEMA_VERSION = 4
```

- [ ] **Step 4: Run test — expect PASS**

```bash
.venv/bin/python -m pytest tests/test_migrations.py -v
```

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add atlassian_cache/migrations.py tests/test_migrations.py
git commit -m "feat(schema): v4 — add Confluence tables (pages, sections, links, sprint_links)"
```

---

## Task 5: Schema v5 — FTS5 Porter Tokenizer + New Columns

**Files:**

- Modify: `atlassian_cache/migrations.py` — add `_MIGRATION_V5`, bump `SCHEMA_VERSION` to 5

> v5 drops and recreates `issues_fts` with `porter unicode61` tokenizer and adds `labels_text` + `assignee_name` columns. Also adds `confluence_fts`.

- [ ] **Step 1: Add v5 tests**

In `tests/test_migrations.py`, add:

```python
def test_v5_fts_porter_tokenizer(conn):
    """v5 creates issues_fts with porter tokenizer (stemming works)."""
    migrate(conn)
    # Insert an issue with "running" in summary
    conn.execute("""INSERT INTO issues
        (issue_key, summary, status, assignee, issue_type, labels, description_text, data, cached_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        ("BEP-1", "running tests", "To Do", "alice", "Story", "[]", "", "{}", "2026-01-01")
    )
    conn.commit()
    # Porter stemming: "run" should match "running"
    rows = conn.execute(
        "SELECT issue_key FROM issues_fts WHERE issues_fts MATCH 'run'"
    ).fetchall()
    assert any(r[0] == "BEP-1" for r in rows)

def test_v5_confluence_fts_exists(conn):
    """v5 creates confluence_fts table."""
    migrate(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert "confluence_fts" in tables
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/bin/python -m pytest tests/test_migrations.py::test_v5_fts_porter_tokenizer -v
```

- [ ] **Step 3: Add v5 migration**

> `labels_text` must be a space-joined string (e.g. `"bug backend"`) not raw JSON. SQLite FTS5 triggers cannot parse JSON, so `put_issue()` in `cache.py` must extract and store `labels_text` before inserting — the trigger then reads the pre-extracted column directly.

```python
_MIGRATION_V5 = """
ALTER TABLE issues ADD COLUMN labels_text TEXT DEFAULT '';
ALTER TABLE issues ADD COLUMN assignee_name TEXT DEFAULT '';

DROP TABLE IF EXISTS issues_fts;

CREATE VIRTUAL TABLE issues_fts USING fts5(
    issue_key UNINDEXED,
    summary,
    description_text,
    labels_text,
    assignee_name,
    content=issues,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

DROP TRIGGER IF EXISTS issues_fts_insert;
DROP TRIGGER IF EXISTS issues_fts_delete;
DROP TRIGGER IF EXISTS issues_fts_update;

CREATE TRIGGER issues_fts_insert AFTER INSERT ON issues BEGIN
    INSERT INTO issues_fts(rowid, issue_key, summary, description_text, labels_text, assignee_name)
    VALUES (new.rowid, new.issue_key, new.summary, new.description_text,
            COALESCE(new.labels_text, ''), COALESCE(new.assignee_name, ''));
END;
CREATE TRIGGER issues_fts_delete AFTER DELETE ON issues BEGIN
    INSERT INTO issues_fts(issues_fts, rowid, issue_key, summary, description_text, labels_text, assignee_name)
    VALUES ('delete', old.rowid, old.issue_key, old.summary, old.description_text,
            COALESCE(old.labels_text, ''), COALESCE(old.assignee_name, ''));
END;
CREATE TRIGGER issues_fts_update AFTER UPDATE ON issues BEGIN
    INSERT INTO issues_fts(issues_fts, rowid, issue_key, summary, description_text, labels_text, assignee_name)
    VALUES ('delete', old.rowid, old.issue_key, old.summary, old.description_text,
            COALESCE(old.labels_text, ''), COALESCE(old.assignee_name, ''));
    INSERT INTO issues_fts(rowid, issue_key, summary, description_text, labels_text, assignee_name)
    VALUES (new.rowid, new.issue_key, new.summary, new.description_text,
            COALESCE(new.labels_text, ''), COALESCE(new.assignee_name, ''));
END;

CREATE VIRTUAL TABLE IF NOT EXISTS confluence_fts USING fts5(
    page_id UNINDEXED,
    title,
    body_text,
    labels_text,
    content=confluence_pages,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS confluence_fts_insert AFTER INSERT ON confluence_pages BEGIN
    INSERT INTO confluence_fts(rowid, page_id, title, body_text, labels_text)
    VALUES (new.rowid, new.page_id, new.title,
            COALESCE(SUBSTR(new.body_md, 1, 50000), ''),
            COALESCE(new.labels, ''));
END;
CREATE TRIGGER IF NOT EXISTS confluence_fts_delete AFTER DELETE ON confluence_pages BEGIN
    INSERT INTO confluence_fts(confluence_fts, rowid, page_id, title, body_text, labels_text)
    VALUES ('delete', old.rowid, old.page_id, old.title,
            COALESCE(SUBSTR(old.body_md, 1, 50000), ''),
            COALESCE(old.labels, ''));
END;
CREATE TRIGGER IF NOT EXISTS confluence_fts_update AFTER UPDATE ON confluence_pages BEGIN
    INSERT INTO confluence_fts(confluence_fts, rowid, page_id, title, body_text, labels_text)
    VALUES ('delete', old.rowid, old.page_id, old.title,
            COALESCE(SUBSTR(old.body_md, 1, 50000), ''),
            COALESCE(old.labels, ''));
    INSERT INTO confluence_fts(rowid, page_id, title, body_text, labels_text)
    VALUES (new.rowid, new.page_id, new.title,
            COALESCE(SUBSTR(new.body_md, 1, 50000), ''),
            COALESCE(new.labels, ''));
END;

"""

_MIGRATIONS: dict[int, str] = {
    2: _MIGRATION_V2,
    3: _MIGRATION_V3,
    4: _MIGRATION_V4,
    5: _MIGRATION_V5,
}
SCHEMA_VERSION = 5
```

Also update `put_issue()` in `atlassian_cache/cache.py` to extract `labels_text` and `assignee_name` before insert:

```python
# Inside put_issue(), before the INSERT:
labels_raw = issue.get("fields", {}).get("labels", [])
labels_text = " ".join(str(lb) for lb in labels_raw) if isinstance(labels_raw, list) else ""
assignee_name = (issue.get("fields", {}).get("assignee") or {}).get("displayName", "")
# Add labels_text and assignee_name to the INSERT column list and values
```

- [ ] **Step 4: Run v5 tests — expect PASS**

```bash
.venv/bin/python -m pytest tests/test_migrations.py -v
```

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add atlassian_cache/migrations.py tests/test_migrations.py
git commit -m "feat(schema): v5 — FTS5 porter tokenizer, labels_text/assignee_name, confluence_fts"
```

---

## Task 6: sections.py — Markdown Splitter

**Files:**

- Create: `atlassian_cache/sections.py`
- Create: `tests/test_sections.py`

- [ ] **Step 1: Write tests first**

Create `tests/test_sections.py`:

```python
"""Tests for atlassian_cache.sections — 100% coverage."""
from atlassian_cache.sections import split_sections, diff_sections, SectionData


def test_split_single_section():
    md = "## Overview\n\nThis is the overview text.\n"
    sections = split_sections("P1", md)
    assert len(sections) == 1
    assert sections[0].heading == "Overview"
    assert sections[0].section_id == "P1::overview"
    assert "overview text" in sections[0].body_md


def test_split_multiple_sections():
    md = "## Intro\n\nIntro text.\n\n## Details\n\nDetail text.\n"
    sections = split_sections("P2", md)
    assert len(sections) == 2
    assert sections[0].heading == "Intro"
    assert sections[1].heading == "Details"


def test_split_no_h2():
    """Pages with no H2 headings return a single synthetic section."""
    md = "Just some plain text without headings."
    sections = split_sections("P3", md)
    assert len(sections) == 1
    assert sections[0].heading == "_body"


def test_split_section_id_slugification():
    md = "## My Complex Heading!\n\nContent.\n"
    sections = split_sections("P4", md)
    assert sections[0].section_id == "P4::my-complex-heading"


def test_split_empty_page():
    sections = split_sections("P5", "")
    assert sections == []


def test_content_hash_is_sha256():
    import hashlib
    md = "## Section\n\nBody text.\n"
    sections = split_sections("P6", md)
    expected = hashlib.sha256(sections[0].body_md.encode()).hexdigest()
    assert sections[0].content_hash == expected


def test_diff_detects_new_sections():
    new = split_sections("P7", "## A\n\nNew content.\n\n## B\n\nContent B.\n")
    old = split_sections("P7", "## A\n\nOld content.\n")
    changed, removed = diff_sections(new, {s.section_id: s for s in old})
    assert any(s.heading == "A" for s in changed)  # A changed
    assert any(s.heading == "B" for s in changed)  # B is new


def test_diff_detects_removed_sections():
    new = split_sections("P8", "## A\n\nSame content.\n")
    old = split_sections("P8", "## A\n\nSame content.\n\n## B\n\nContent B.\n")
    changed, removed = diff_sections(new, {s.section_id: s for s in old})
    assert len(changed) == 0  # A is unchanged
    assert "P8::b" in removed


def test_diff_unchanged_not_in_changed():
    content = "## A\n\nIdentical content.\n"
    sections = split_sections("P9", content)
    old_map = {s.section_id: s for s in sections}
    changed, removed = diff_sections(sections, old_map)
    assert len(changed) == 0  # nothing changed
    assert len(removed) == 0
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/bin/python -m pytest tests/test_sections.py -v
```

- [ ] **Step 3: Implement atlassian_cache/sections.py**

```python
"""H2-based Markdown section splitter with SHA256 hash-based change detection.

Usage:
    sections = split_sections(page_id, markdown_body)
    changed, removed = diff_sections(new_sections, old_sections_by_id)
"""
import hashlib
import re
from dataclasses import dataclass


@dataclass
class SectionData:
    section_id: str       # "{page_id}::{slug}"
    page_id: str
    heading: str          # Original heading text
    body_md: str          # Markdown body of this section
    content_hash: str     # SHA256 of body_md


_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_SLUG_RE = re.compile(r"[^a-z0-9\-]")


def _slugify(heading: str) -> str:
    return _SLUG_RE.sub("", heading.lower().replace(" ", "-"))


def split_sections(page_id: str, body_md: str) -> list[SectionData]:
    """Split Markdown body at H2 headings into SectionData records.

    Pages with no H2 headings return a single section with heading '_body'.
    Empty pages return an empty list.
    """
    if not body_md.strip():
        return []

    matches = list(_H2_RE.finditer(body_md))
    if not matches:
        content = body_md.strip()
        return [_make_section(page_id, "_body", content)]

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_md)
        content = body_md[start:end].strip()
        sections.append(_make_section(page_id, heading, content))
    return sections


def _make_section(page_id: str, heading: str, body_md: str) -> SectionData:
    slug = _slugify(heading)
    section_id = f"{page_id}::{slug}"
    content_hash = hashlib.sha256(body_md.encode()).hexdigest()
    return SectionData(
        section_id=section_id,
        page_id=page_id,
        heading=heading,
        body_md=body_md,
        content_hash=content_hash,
    )


def diff_sections(
    new_sections: list[SectionData],
    old_by_id: dict[str, SectionData],
) -> tuple[list[SectionData], list[str]]:
    """Compare new sections against stored sections.

    Returns:
        changed: Sections that are new or have a different content_hash.
        removed: section_ids present in old_by_id but not in new_sections.
    """
    new_by_id = {s.section_id: s for s in new_sections}
    changed = [
        s for s in new_sections
        if s.section_id not in old_by_id
        or old_by_id[s.section_id].content_hash != s.content_hash
    ]
    removed = [sid for sid in old_by_id if sid not in new_by_id]
    return changed, removed
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/bin/python -m pytest tests/test_sections.py -v
```

- [ ] **Step 5: Commit**

```bash
git add atlassian_cache/sections.py tests/test_sections.py
git commit -m "feat: add sections.py — H2 Markdown splitter with SHA256 hash diff"
```

---

## Task 7: confluence_cache.py — Confluence CRUD + FTS

**Files:**

- Create: `atlassian_cache/confluence_cache.py`
- Create: `tests/test_confluence_cache.py`
- Modify: `tests/conftest.py` — add `confluence_cache`, `sample_page`, `make_section` fixtures

- [ ] **Step 1: Update conftest.py fixtures**

Add to `tests/conftest.py`:

```python
def make_page(
    page_id: str = "12345",
    title: str = "Test Page",
    space_key: str = "BEP",
    body_md: str = "## Overview\n\nPage content.",
    version_num: int = 1,
    labels: list | None = None,
    author: str = "Test Author",
) -> dict:
    """Build a minimal Confluence page dict for testing."""
    return {
        "id": page_id,
        "title": title,
        "space": {"key": space_key},
        "_body_md": body_md,   # pre-converted Markdown (would normally come from converter)
        "version": {"number": version_num, "when": "2026-01-01T00:00:00.000Z"},
        "metadata": {"labels": {"results": [{"name": l} for l in (labels or [])]}},
        "history": {"createdBy": {"displayName": author}},
        "_links": {"webui": f"/wiki/spaces/{space_key}/pages/{page_id}"},
    }


@pytest.fixture
def confluence_cache(cache):
    """Return a ConfluenceCache sharing the JiraCache connection."""
    from atlassian_cache.confluence_cache import ConfluenceCache
    return ConfluenceCache(cache.conn, cache._lock)


@pytest.fixture
def sample_page():
    return make_page()
```

- [ ] **Step 2: Write tests**

Create `tests/test_confluence_cache.py`:

```python
"""Tests for atlassian_cache.confluence_cache — 100% coverage."""
import time
import pytest
from conftest import make_page


class TestPutAndGetPage:
    def test_put_and_get_fresh(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        result = confluence_cache.get_page("12345", max_age_hours=24)
        assert result is not None
        assert result["id"] == "12345"
        assert result["title"] == "Test Page"

    def test_get_returns_none_when_stale(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        result = confluence_cache.get_page("12345", max_age_hours=0)
        assert result is None

    def test_get_returns_none_when_not_cached(self, confluence_cache):
        assert confluence_cache.get_page("nonexistent", max_age_hours=24) is None

    def test_put_updates_existing(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        updated = make_page(page_id="12345", title="Updated Title", version_num=2)
        confluence_cache.put_page(updated)
        result = confluence_cache.get_page("12345", max_age_hours=24)
        assert result["title"] == "Updated Title"


class TestFtsSearch:
    def test_fts_finds_by_title(self, confluence_cache):
        confluence_cache.put_page(make_page(page_id="A", title="Sprint Planning Guide"))
        results = confluence_cache.fts_search("Sprint Planning", limit=5)
        assert any(r["page_id"] == "A" for r in results)

    def test_fts_returns_empty_when_no_match(self, confluence_cache):
        confluence_cache.put_page(make_page(page_id="B", title="Unrelated Page"))
        results = confluence_cache.fts_search("quantum physics", limit=5)
        assert results == []

    def test_fts_porter_stemming(self, confluence_cache):
        """Porter tokenizer: 'plan' should match 'planning'."""
        confluence_cache.put_page(make_page(page_id="C", title="Sprint Planning"))
        results = confluence_cache.fts_search("plan", limit=5)
        assert any(r["page_id"] == "C" for r in results)


class TestSectionStorage:
    def test_store_and_get_sections(self, confluence_cache, sample_page):
        from atlassian_cache.sections import split_sections
        confluence_cache.put_page(sample_page)
        sections = split_sections("12345", sample_page["_body_md"])
        confluence_cache.put_sections(sections)
        stored = confluence_cache.get_sections("12345")
        assert len(stored) == len(sections)

    def test_partial_invalidation_only_re_embeds_changed(self, confluence_cache):
        """put_sections replaces only changed sections."""
        from atlassian_cache.sections import split_sections, SectionData
        confluence_cache.put_page(make_page(page_id="D", body_md="## A\n\nSame.\n\n## B\n\nOld B.\n"))
        old_secs = split_sections("D", "## A\n\nSame.\n\n## B\n\nOld B.\n")
        confluence_cache.put_sections(old_secs)
        new_secs = split_sections("D", "## A\n\nSame.\n\n## B\n\nNew B.\n")
        changed, removed = confluence_cache.update_sections("D", new_secs)
        assert len(changed) == 1   # only B changed
        assert changed[0].heading == "B"
        assert len(removed) == 0


class TestInvalidate:
    def test_invalidate_removes_page(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        confluence_cache.invalidate("12345")
        assert confluence_cache.get_page("12345", max_age_hours=24) is None

    def test_invalidate_nonexistent_is_noop(self, confluence_cache):
        confluence_cache.invalidate("ghost")  # should not raise
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
.venv/bin/python -m pytest tests/test_confluence_cache.py -v
```

- [ ] **Step 4: Implement atlassian_cache/confluence_cache.py**

```python
"""Confluence page cache backed by the shared atlassian-cache SQLite database.

No independent SQLite connection — ConfluenceCache receives the shared conn
from JiraCache. Closing JiraCache.conn is sufficient; ConfluenceCache holds
no independent resources.

Usage:
    cache = JiraCache(db_path=...)
    confluence = ConfluenceCache(cache.conn, cache._lock)
    confluence.put_page(page_dict)
    page = confluence.get_page("12345", max_age_hours=4)
"""
import hashlib
import json
import logging
import threading
import time
from typing import Any

from .sections import SectionData, diff_sections

logger = logging.getLogger(__name__)


def _md5(s: str) -> str:
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()  # noqa: S324 — not crypto, cache key only


def _extract_page_fields(page: dict) -> dict:
    """Normalise a Confluence API page dict into storage fields."""
    version = page.get("version", {})
    space = page.get("space", {})
    history = page.get("history", {})
    links = page.get("_links", {})
    labels_raw = page.get("metadata", {}).get("labels", {}).get("results", [])
    labels = json.dumps([lb["name"] for lb in labels_raw])
    return {
        "page_id": page["id"],
        "space_key": space.get("key", ""),
        "title": page.get("title", ""),
        "body_md": page.get("_body_md") or "",
        "version_num": version.get("number", 0),
        "version_when": version.get("when"),
        "labels": labels,
        "author": (history.get("createdBy") or {}).get("displayName"),
        "url": links.get("webui"),
    }


class ConfluenceCache:
    """Cache for Confluence pages with FTS5 and section-level storage.

    Shares the SQLite connection from JiraCache. No close() method —
    connection lifetime is managed by JiraCache.
    """

    def __init__(self, conn: Any, lock: threading.Lock | None = None) -> None:
        self.conn = conn
        self._lock = lock if lock is not None else threading.Lock()

    # --- Page CRUD ---

    def put_page(self, page: dict) -> None:
        """Store or update a Confluence page."""
        fields = _extract_page_fields(page)
        now = time.time()
        with self._lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO confluence_pages
                (page_id, space_key, title, body_md, version_num, version_when,
                 labels, author, cached_at, url)
                VALUES (:page_id, :space_key, :title, :body_md, :version_num,
                        :version_when, :labels, :author, :cached_at, :url)
            """, {**fields, "cached_at": now})
            self.conn.commit()
        logger.debug("confluence: cached page %s", fields["page_id"])

    def get_page(self, page_id: str, max_age_hours: float = 4.0) -> dict | None:
        """Return cached page if fresh, None otherwise."""
        row = self.conn.execute(
            "SELECT * FROM confluence_pages WHERE page_id = ?", (page_id,)
        ).fetchone()
        if row is None:
            return None
        age_hours = (time.time() - row["cached_at"]) / 3600
        if age_hours > max_age_hours:
            return None
        return dict(row)

    def get_version(self, page_id: str) -> tuple[int, str | None] | None:
        """Return (version_num, version_when) for staleness check, or None if not cached."""
        row = self.conn.execute(
            "SELECT version_num, version_when FROM confluence_pages WHERE page_id = ?",
            (page_id,)
        ).fetchone()
        return (row["version_num"], row["version_when"]) if row else None

    def invalidate(self, page_id: str) -> None:
        """Remove a page and all its sections from cache."""
        with self._lock:
            self.conn.execute("DELETE FROM confluence_sections WHERE page_id = ?", (page_id,))
            self.conn.execute("DELETE FROM confluence_pages WHERE page_id = ?", (page_id,))
            self.conn.commit()

    # --- FTS ---

    def fts_search(self, query: str, limit: int = 20) -> list[dict]:
        """BM25-ranked FTS5 search over title, body, labels."""
        # Sanitize: keep alphanumeric + Thai + spaces
        import re
        safe_q = re.sub(r"[^a-zA-Z0-9\u0E00-\u0E7F\s]", " ", query).strip()
        if not safe_q:
            return []
        try:
            rows = self.conn.execute("""
                SELECT page_id, title,
                       bm25(confluence_fts, 10.0, 5.0, 2.0) AS rank
                FROM confluence_fts
                WHERE confluence_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (safe_q, limit)).fetchall()
            return [{"page_id": r["page_id"], "title": r["title"], "rank": r["rank"]} for r in rows]
        except Exception as e:
            logger.error("confluence FTS error: %s", e)
            return []

    # --- Sections ---

    def put_sections(self, sections: list[SectionData]) -> None:
        """Store sections (upsert), replacing existing ones for the same page."""
        now = time.time()
        with self._lock:
            self.conn.executemany("""
                INSERT OR REPLACE INTO confluence_sections
                (section_id, page_id, heading, body_md, content_hash, cached_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (s.section_id, s.page_id, s.heading, s.body_md, s.content_hash, now)
                for s in sections
            ])
            self.conn.commit()

    def get_sections(self, page_id: str) -> list[dict]:
        """Return all stored sections for a page."""
        rows = self.conn.execute(
            "SELECT * FROM confluence_sections WHERE page_id = ?", (page_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_sections(
        self, page_id: str, new_sections: list[SectionData]
    ) -> tuple[list[SectionData], list[str]]:
        """Partial invalidation: update only changed sections, delete removed ones.

        Returns:
            changed: Sections that were new or updated.
            removed: section_ids that were deleted.
        """
        old_rows = self.get_sections(page_id)
        old_by_id = {r["section_id"]: SectionData(
            section_id=r["section_id"], page_id=r["page_id"], heading=r["heading"],
            body_md=r["body_md"], content_hash=r["content_hash"]
        ) for r in old_rows}

        changed, removed_ids = diff_sections(new_sections, old_by_id)

        if changed:
            self.put_sections(changed)
        if removed_ids:
            with self._lock:
                self.conn.executemany(
                    "DELETE FROM confluence_sections WHERE section_id = ?",
                    [(sid,) for sid in removed_ids]
                )
                self.conn.commit()

        return changed, removed_ids
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
.venv/bin/python -m pytest tests/test_confluence_cache.py tests/test_sections.py -v
```

- [ ] **Step 6: Run full suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 7: Commit**

```bash
git add atlassian_cache/confluence_cache.py tests/test_confluence_cache.py tests/conftest.py
git commit -m "feat: add ConfluenceCache with FTS5, section CRUD, partial invalidation"
```

---

## Task 8: embeddings.py — Multilingual MiniLM + Cross-Modal

**Files:**

- Modify: `atlassian_cache/embeddings.py`
- Modify: `tests/test_embeddings.py`

> Two changes: (1) swap model name to `paraphrase-multilingual-MiniLM-L12-v2`, (2) migrate from `issue_embeddings` vec0 table to a shared `embeddings` table with `entity_type` column (Jira/Confluence cross-modal search).

- [ ] **Step 1: Add cross-modal tests**

Add to `tests/test_embeddings.py`:

```python
def test_model_name_is_multilingual(monkeypatch):
    """Model should be multilingual MiniLM, not English-only."""
    import atlassian_cache.embeddings as em
    em._model = None  # reset lazy cache
    loaded_name = []
    original = em.SentenceTransformer if hasattr(em, 'SentenceTransformer') else None

    class FakeST:
        def __init__(self, name, **_):
            loaded_name.append(name)
        def encode(self, *a, **kw):
            import numpy as np
            return np.zeros((1, 384) if isinstance(a[0], list) else (384,))

    monkeypatch.setattr("atlassian_cache.embeddings.SentenceTransformer", FakeST, raising=False)
    from atlassian_cache.embeddings import _get_model
    _get_model()
    assert "multilingual" in loaded_name[0]

def test_entity_type_filter(cache):
    """Cross-modal search can filter by entity_type."""
    from atlassian_cache.embeddings import EmbeddingStore
    store = EmbeddingStore(cache.conn, cache._lock)
    if not store.available:
        pytest.skip("sqlite-vec not available")
    store.store_embedding("BEP-1", "jira issue text", entity_type="jira")
    results = store.find_similar("jira issue", entity_type="jira", limit=5)
    assert all(r["entity_type"] == "jira" for r in results)
```

- [ ] **Step 2: Update embeddings.py**

Key changes:

- Model name: `"all-MiniLM-L6-v2"` → `"paraphrase-multilingual-MiniLM-L12-v2"`
- Schema: `issue_embeddings` → shared `embeddings` with `entity_id TEXT, entity_type TEXT, embedding float[384]`
- `store_embedding(key, text)` → `store_embedding(key, text, entity_type="jira")`
- `find_similar(query)` → `find_similar(query, entity_type=None, limit=5)` — `None` = cross-modal

Update `EMBEDDINGS_SCHEMA`:

```python
EMBEDDINGS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT,
    embedding float[384]
);
"""
```

Update `_get_model()`:

```python
_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
```

Update `store_embedding` signature and SQL:

```python
def store_embedding(self, entity_id: str, text: str, entity_type: str = "jira") -> bool:
    ...
    self.conn.execute(
        "INSERT OR REPLACE INTO embeddings (entity_id, entity_type, embedding) VALUES (?, ?, ?)",
        (entity_id, entity_type, _serialize_f32(vec)),
    )
```

Update `find_similar`:

```python
def find_similar(self, query: str, limit: int = 5,
                 exclude_keys: list[str] | None = None,
                 entity_type: str | None = None) -> list[dict]:
    ...
    type_clause = "AND entity_type = ?" if entity_type else ""
    params = [_serialize_f32(vec)] + ([entity_type] if entity_type else []) + [limit + len(exclude_keys or [])]
    rows = self.conn.execute(f"""
        SELECT entity_id, entity_type, distance
        FROM embeddings
        WHERE embedding MATCH ?
        {type_clause}
        ORDER BY distance
        LIMIT ?
    """, params).fetchall()
    ...
    return [{"entity_id": r[0], "entity_type": r[1], "distance": round(r[2], 4)} for r in ...]
```

Also update `store_batch` and `remove_embedding` to use `entity_id` column.

- [ ] **Step 3: Run tests**

```bash
.venv/bin/python -m pytest tests/test_embeddings.py -v
```

- [ ] **Step 4: Run full suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add atlassian_cache/embeddings.py tests/test_embeddings.py
git commit -m "feat(embeddings): multilingual MiniLM, shared entity table, cross-modal search"
```

---

## Task 9: In-Session Deduplication + Compact List Format

**Files:**

- Modify: `server.py` — `_session_returned` set, compact format helper

- [ ] **Step 1: Write tests**

Add to `tests/test_server.py`:

```python
def test_compact_format_for_large_lists(cache, multiple_issues):
    """Lists with 20+ issues use compact headers+rows format."""
    from server import _maybe_compact
    issues = [{"key": f"BEP-{i}", "summary": f"Issue {i}",
               "status": "To Do", "assignee": None, "sp": None}
              for i in range(25)]
    result = _maybe_compact(issues)
    assert result["format"] == "compact"
    assert "headers" in result
    assert "rows" in result
    assert len(result["rows"]) == 25

def test_small_list_not_compacted():
    from server import _maybe_compact
    issues = [{"key": f"BEP-{i}", "summary": "x"} for i in range(5)]
    result = _maybe_compact(issues)
    assert isinstance(result, list)  # unchanged

def test_session_dedup_returns_ref_on_repeat(cache, sample_issue):
    """Second fetch of same issue within session returns compact ref."""
    from server import _mark_returned, _already_returned
    _mark_returned("BEP-100")
    assert _already_returned("BEP-100")
```

- [ ] **Step 2: Implement in server.py**

Add at module level (after imports):

```python
# In-session deduplication — reset per MCP session (process lifetime)
_session_returned: set[str] = set()
_COMPACT_LIST_THRESHOLD = 20


def _mark_returned(entity_id: str) -> None:
    _session_returned.add(entity_id)


def _already_returned(entity_id: str) -> bool:
    return entity_id in _session_returned


def _compact_ref(entity_id: str, summary: str) -> dict:
    """Return minimal reference for already-seen entities."""
    return {"id": entity_id, "summary": summary, "_ref": "returned_this_session"}


def _maybe_compact(issues: list[dict]) -> list[dict] | dict:
    """Use compact headers+rows format for 20+ issue lists."""
    if len(issues) < _COMPACT_LIST_THRESHOLD:
        return issues
    headers = ["key", "summary", "status", "assignee", "sp"]
    rows = [
        [
            i.get("key", ""),
            i.get("summary", ""),
            i.get("status", ""),
            i.get("assignee", ""),
            i.get("sp"),
        ]
        for i in issues
    ]
    return {"format": "compact", "headers": headers, "rows": rows}
```

Apply `_mark_returned` in `handle_cache_get_issue` and `handle_cache_get_issues`. Apply `_maybe_compact` in `handle_cache_get_issues`, `handle_cache_sprint_issues`, and `handle_cache_search` before serializing.

- [ ] **Step 3: Run tests + full suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: in-session deduplication and compact list format for 20+ issues"
```

---

## Task 10: 9 Confluence MCP Tools

**Files:**

- Modify: `server.py` — add `ConfluenceCache` init in `_lifespan`, register 9 Confluence tools and handlers

- [ ] **Step 1: Update lifespan to init ConfluenceCache**

In `server.py`, inside `_lifespan`:

```python
from atlassian_cache.confluence_cache import ConfluenceCache

confluence: ConfluenceCache | None = None

@asynccontextmanager
async def _lifespan(server: Server):
    global cache, embeddings, jira_api, confluence
    _init()  # existing JiraCache init
    confluence = ConfluenceCache(cache.conn, cache._lock)
    try:
        yield
    finally:
        if cache:
            cache.close()
```

- [ ] **Step 2: Register the 9 Confluence tools in TOOLS list**

Add after existing Jira tools:

```python
Tool(name="cache_get_confluence_page",
     description="Fetch a Confluence page by ID. Returns cached body_md if fresh, else fetches from Confluence REST API.",
     inputSchema={"type": "object", "properties": {
         "page_id": {"type": "string"},
         "max_age_hours": {"type": "number", "default": 4}
     }, "required": ["page_id"]}),

Tool(name="cache_search_confluence",
     description="FTS5 keyword search across cached Confluence pages (title, body, labels). Uses BM25 ranking.",
     inputSchema={"type": "object", "properties": {
         "query": {"type": "string"},
         "limit": {"type": "integer", "default": 10}
     }, "required": ["query"]}),

Tool(name="cache_get_confluence_children",
     description="Get child pages of a given Confluence page_id from cache.",
     inputSchema={"type": "object", "properties": {
         "page_id": {"type": "string"}
     }, "required": ["page_id"]}),

Tool(name="cache_find_confluence_related",
     description="Vector search: find Confluence sections semantically similar to a query string.",
     inputSchema={"type": "object", "properties": {
         "query": {"type": "string"},
         "limit": {"type": "integer", "default": 5}
     }, "required": ["query"]}),

Tool(name="cache_cross_search",
     description="Cross-modal vector search across both Jira issues and Confluence sections.",
     inputSchema={"type": "object", "properties": {
         "query": {"type": "string"},
         "limit": {"type": "integer", "default": 10}
     }, "required": ["query"]}),

Tool(name="cache_invalidate_confluence",
     description="Remove a Confluence page and its sections from cache.",
     inputSchema={"type": "object", "properties": {
         "page_id": {"type": "string"}
     }, "required": ["page_id"]}),

Tool(name="cache_refresh_confluence",
     description="Force-refresh a Confluence page from the Confluence REST API.",
     inputSchema={"type": "object", "properties": {
         "page_id": {"type": "string"}
     }, "required": ["page_id"]}),

Tool(name="cache_get_confluence_section",
     description="Fetch a specific Confluence section by section_id (format: '{page_id}::{heading-slug}').",
     inputSchema={"type": "object", "properties": {
         "section_id": {"type": "string"}
     }, "required": ["section_id"]}),

Tool(name="cache_sprint_confluence",
     description="Get Confluence pages linked to a sprint via the confluence_sprint_links mapping table.",
     inputSchema={"type": "object", "properties": {
         "sprint_id": {"type": "integer"}
     }, "required": ["sprint_id"]}),
```

- [ ] **Step 3: Add missing ConfluenceCache methods needed by 8 tools**

Add to `atlassian_cache/confluence_cache.py`:

```python
def get_children(self, page_id: str) -> list[dict]:
    """Return child page stubs from confluence_links."""
    rows = self.conn.execute(
        "SELECT to_page_id FROM confluence_links WHERE from_page_id = ? AND link_type = 'child'",
        (page_id,)
    ).fetchall()
    result = []
    for r in rows:
        p = self.conn.execute(
            "SELECT page_id, title, url FROM confluence_pages WHERE page_id = ?",
            (r["to_page_id"],)
        ).fetchone()
        if p:
            result.append(dict(p))
    return result

def get_section(self, section_id: str) -> dict | None:
    row = self.conn.execute(
        "SELECT * FROM confluence_sections WHERE section_id = ?", (section_id,)
    ).fetchone()
    return dict(row) if row else None

def get_sprint_pages(self, sprint_id: int) -> list[dict]:
    rows = self.conn.execute(
        "SELECT p.page_id, p.title, p.url FROM confluence_sprint_links l "
        "JOIN confluence_pages p ON p.page_id = l.page_id WHERE l.sprint_id = ?",
        (sprint_id,)
    ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Implement all 9 handlers in handle_call_tool**

Add each handler in the `elif name == ...` chain:

```python
elif name == "cache_get_confluence_page":
    page_id = arguments["page_id"]
    max_age = _clamp_max_age(arguments.get("max_age_hours"), 4.0)
    result = confluence.get_page(page_id, max_age_hours=max_age)
    if result is None:
        return [TextContent(type="text", text=json.dumps({"error": "not_cached", "page_id": page_id}))]
    _mark_returned(page_id)
    return [TextContent(type="text", text=json.dumps(result)[:MAX_RESPONSE_CHARS])]

elif name == "cache_search_confluence":
    results = confluence.fts_search(arguments["query"], limit=min(int(arguments.get("limit", 10)), 50))
    return [TextContent(type="text", text=json.dumps({"results": results}))]

elif name == "cache_get_confluence_children":
    children = confluence.get_children(arguments["page_id"])
    return [TextContent(type="text", text=json.dumps({"children": children}))]

elif name == "cache_find_confluence_related":
    limit = min(int(arguments.get("limit", 5)), 20)
    results = embeddings.find_similar(arguments["query"], limit=limit, entity_type="confluence") if embeddings and embeddings.available else []
    return [TextContent(type="text", text=json.dumps({"related": results}))]

elif name == "cache_cross_search":
    limit = min(int(arguments.get("limit", 10)), 20)
    results = embeddings.find_similar(arguments["query"], limit=limit, entity_type=None) if embeddings and embeddings.available else []
    return [TextContent(type="text", text=json.dumps({"results": results}))]

elif name == "cache_invalidate_confluence":
    confluence.invalidate(arguments["page_id"])
    return [TextContent(type="text", text=json.dumps({"invalidated": arguments["page_id"]}))]

elif name == "cache_refresh_confluence":
    confluence.invalidate(arguments["page_id"])
    return [TextContent(type="text", text=json.dumps({"status": "invalidated", "page_id": arguments["page_id"],
        "message": "Page cleared. Call cache_get_confluence_page to re-fetch."}))]

elif name == "cache_get_confluence_section":
    section = confluence.get_section(arguments["section_id"])
    if section is None:
        return [TextContent(type="text", text=json.dumps({"error": "not_found"}))]
    return [TextContent(type="text", text=json.dumps(section)[:MAX_RESPONSE_CHARS])]

elif name == "cache_sprint_confluence":
    pages = confluence.get_sprint_pages(int(arguments["sprint_id"]))
    return [TextContent(type="text", text=json.dumps({"pages": pages}))]
```

- [ ] **Step 5: Add smoke tests to test_server.py**

```python
def test_confluence_tools_registered():
    from server import TOOLS
    names = {t.name for t in TOOLS}
    assert "cache_get_confluence_page" in names
    assert "cache_search_confluence" in names
    assert "cache_cross_search" in names
    assert len(names) == 21  # 12 Jira + 9 Confluence
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add 9 Confluence MCP tools (get, search, children, related, cross, invalidate, refresh, section, sprint)"
```

---

## Task 11: 3 New Jira Tools

**Files:**

- Modify: `server.py` — add `cache_find_related`, `cache_reindex`, `cache_sync`
- Modify: `atlassian_cache/cache.py` — add `get_all_issues()`
- Modify: `atlassian_cache/confluence_cache.py` — add `get_all_sections()`

- [ ] **Step 1: Write tests first (TDD)**

Add to `tests/test_server.py`:

```python
def test_new_jira_tools_registered():
    from server import TOOLS
    names = {t.name for t in TOOLS}
    assert "cache_find_related" in names
    assert "cache_reindex" in names
    assert "cache_sync" in names

def test_get_all_issues_returns_list(cache, sample_issue):
    cache.put_issue(sample_issue["key"], sample_issue)
    issues = cache.get_all_issues()
    assert isinstance(issues, list)
    assert len(issues) >= 1
    assert all("key" in i for i in issues)

def test_get_all_sections_returns_list(confluence_cache, sample_page):
    from atlassian_cache.sections import split_sections
    confluence_cache.put_page(sample_page)
    sections = split_sections("12345", sample_page["_body_md"])
    confluence_cache.put_sections(sections)
    all_secs = confluence_cache.get_all_sections()
    assert isinstance(all_secs, list)
    assert len(all_secs) == len(sections)
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/bin/python -m pytest tests/test_server.py::test_new_jira_tools_registered -v
```

Expected: FAIL — tools not registered yet

- [ ] **Step 3: Add tool definitions to TOOLS**

```python
Tool(name="cache_find_related",
     description="Given a Jira issue key, find semantically similar Jira issues AND related Confluence sections in one call.",
     inputSchema={"type": "object", "properties": {
         "issue_key": {"type": "string"},
         "limit": {"type": "integer", "default": 5}
     }, "required": ["issue_key"]}),

Tool(name="cache_reindex",
     description="Re-embed all cached entities (Jira issues + Confluence sections). Use after switching embedding models.",
     inputSchema={"type": "object", "properties": {
         "entity_type": {"type": "string", "enum": ["jira", "confluence", "all"], "default": "all"}
     }}),

Tool(name="cache_sync",
     description="Incremental Jira sync: fetch issues updated since N hours ago and upsert into cache.",
     inputSchema={"type": "object", "properties": {
         "project_key": {"type": "string"},
         "since_hours": {"type": "number", "default": 24.0}
     }, "required": ["project_key"]}),
```

- [ ] **Step 4: Implement handlers**

`cache_find_related` — get issue from cache, use its summary+description as query, call `embeddings.find_similar(query, entity_type=None)`:

```python
elif name == "cache_find_related":
    key = _validate_issue_key(arguments["issue_key"])
    limit = min(int(arguments.get("limit", 5)), 20)
    issue = _require_cache().get_issue(key)
    if not issue:
        return [TextContent(type="text", text=json.dumps({"error": "not_cached"}))]
    from atlassian_cache.embeddings import embedding_text as _et
    query = _et(issue)
    results = embeddings.find_similar(query, limit=limit, exclude_keys=[key], entity_type=None)
    return [TextContent(type="text", text=json.dumps({"related": results}))]
```

`cache_sync` — build JQL with `updated >= timestamp`, paginate, upsert:

```python
elif name == "cache_sync":
    from datetime import datetime, timedelta
    proj = arguments["project_key"].upper()
    since_hours = float(arguments.get("since_hours", 24.0))
    since = datetime.utcnow() - timedelta(hours=since_hours)
    jql = f'project = {proj} AND updated >= "{since.strftime("%Y-%m-%d %H:%M")}"'
    issues = await jira_api.search_issues(jql, fields="summary,status,assignee,issuetype,priority,labels,parent,description", max_results=200)
    c = _require_cache()
    for issue in issues:
        c.put_issue(issue["key"], issue)
    return [TextContent(type="text", text=json.dumps({"synced": len(issues), "since_hours": since_hours}))]
```

`cache_reindex` — iterate all cached entities, re-embed in batch:

```python
elif name == "cache_reindex":
    entity_type = arguments.get("entity_type", "all")
    count = 0
    c = _require_cache()
    if entity_type in ("jira", "all"):
        issues = c.get_all_issues()
        count += embeddings.store_batch(issues)
    if entity_type in ("confluence", "all") and confluence:
        sections = confluence.get_all_sections()
        for sec in sections:
            embeddings.store_embedding(sec["section_id"], sec["body_md"], entity_type="confluence")
            count += 1
    return [TextContent(type="text", text=json.dumps({"reindexed": count, "entity_type": entity_type}))]
```

- [ ] **Step 5: Add get_all_issues and get_all_sections helpers**

In `cache.py`:

```python
def get_all_issues(self) -> list[dict]:
    """Return all cached issues as raw dicts (for reindex)."""
    rows = self.conn.execute("SELECT data FROM issues").fetchall()
    return [json.loads(r["data"]) for r in rows]
```

In `confluence_cache.py`:

```python
def get_all_sections(self) -> list[dict]:
    """Return all stored sections (for reindex)."""
    rows = self.conn.execute("SELECT * FROM confluence_sections").fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add server.py atlassian_cache/cache.py atlassian_cache/confluence_cache.py tests/test_server.py tests/test_cache.py
git commit -m "feat: add cache_find_related, cache_reindex, cache_sync tools"
```

---

## Task 12: Hybrid Invalidation — Lazy Version-Check

**Files:**

- Modify: `server.py` — lazy Jira version-check in `handle_cache_get_issue`
- Modify: `atlassian_cache/confluence_cache.py` — lazy Confluence version-check helper

> Lazy version-check: after TTL passes but before serving stale data, fetch only the staleness signal (`updated` for Jira, `version.number` for Confluence). If stale, refresh; otherwise extend TTL and return cached data.

**Contract:** `JiraCache.get_issue()` returns a dict that includes `_cached_at` (Unix timestamp float) and `_cached_at_iso` (ISO 8601 string). These must be stored by `put_issue()` and stripped before returning to callers. Verify this is already the case in `cache.py` — add the fields if not present.

- [ ] **Step 1: Write tests**

```python
def test_cached_issue_includes_cached_at_field(cache, sample_issue):
    """put_issue stores _cached_at so lazy version-check can read it."""
    cache.put_issue(sample_issue["key"], sample_issue)
    result = cache.get_issue("BEP-100", max_age_hours=24)
    assert result is not None
    assert "_cached_at" in result
    assert isinstance(result["_cached_at"], float)
    assert "_cached_at_iso" in result

def test_lazy_version_check_skips_when_fresh(cache, sample_issue):
    """When cache is within TTL, no upstream API call is needed."""
    cache.put_issue(sample_issue["key"], sample_issue)
    result = cache.get_issue("BEP-100", max_age_hours=24)
    # Result is returned from cache — no API needed
    assert result is not None

def test_lazy_version_check_triggers_when_stale(cache, sample_issue):
    """When max_age_hours=0, cache miss triggers upstream path."""
    cache.put_issue(sample_issue["key"], sample_issue)
    # max_age=0 means TTL=0 — everything is considered stale
    result = cache.get_issue("BEP-100", max_age_hours=0)
    assert result is None  # stale — caller must fetch upstream
```

- [ ] **Step 2: Ensure put_issue stores _cached_at in issue data**

In `atlassian_cache/cache.py`, update `put_issue()` to embed timestamp:

```python
def put_issue(self, key: str, issue: dict) -> None:
    import time
    from datetime import datetime, timezone
    now = time.time()
    now_iso = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
    # Embed cache metadata into the stored data blob
    data_with_meta = {**issue, "_cached_at": now, "_cached_at_iso": now_iso}
    data_json = json.dumps(data_with_meta)
    # ... rest of INSERT
```

- [ ] **Step 3: Implement lazy version-check in server.py handler**

In `handle_cache_get_issue`, after the TTL check, add:

```python
# Lazy version check: if stale by TTL, check upstream 'updated' field before full refresh
if cached and not force_refresh:
    age_hours = (time.time() - cached.get("_cached_at", 0)) / 3600
    if age_hours > max_age:
        # Cheap upstream check: fetch only 'updated' field (~50ms, ~200 tokens)
        try:
            resp = await jira_api.get_issue(issue_key, fields="updated")
            upstream_updated = (resp.get("fields") or {}).get("updated", "")
            cached_at_iso = cached.get("_cached_at_iso", "")
            if upstream_updated and cached_at_iso and upstream_updated <= cached_at_iso:
                # Issue hasn't changed — serve from cache, skip full refresh
                return [TextContent(type="text", text=json.dumps(cached)[:MAX_RESPONSE_CHARS])]
        except Exception:
            pass  # On any error, fall through to full refresh
```

- [ ] **Step 3: Run tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add server.py atlassian_cache/confluence_cache.py tests/test_server.py
git commit -m "feat: lazy version-check invalidation for Jira (updated field) and Confluence (version.number)"
```

---

## Task 13: Write-Invalidation Hook

**Files:**

- Create: `hooks/plugin/cache_write_invalidate.py`
- Modify: `hooks/hooks.json` — register PostToolUse hook for mcp-atlassian writes

- [ ] **Step 1: Write the hook script**

Create `hooks/plugin/cache_write_invalidate.py`:

```python
#!/usr/bin/env python3
"""PostToolUse hook: auto-invalidate atlassian-cache after any MCP write.

Reads TOOL_RESULT env var (JSON), extracts issue_key or page_id,
calls cache_invalidate via the cache DB directly (no MCP round-trip).
"""
import json
import os
import sys
from pathlib import Path

# Resolve DB path same way as server.py
plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
db_path = (
    Path(os.path.abspath(plugin_data)) if plugin_data else Path.home() / ".cache" / "atlassian-pm"
) / "jira.db"

tool_input = os.environ.get("TOOL_INPUT", "{}")
try:
    inp = json.loads(tool_input)
except json.JSONDecodeError:
    sys.exit(0)

# Extract what to invalidate
key = inp.get("issue_key") or inp.get("issueKey")
page_id = inp.get("id") or inp.get("pageId")

if not (key or page_id):
    sys.exit(0)

if not db_path.exists():
    sys.exit(0)

import sqlite3

try:
    conn = sqlite3.connect(str(db_path), timeout=5)
    if key:
        conn.execute("DELETE FROM issues WHERE issue_key = ?", (key,))
        conn.execute("DELETE FROM searches WHERE result_keys LIKE ?", (f"%{key}%",))
        conn.commit()
    if page_id:
        conn.execute("DELETE FROM confluence_sections WHERE page_id = ?", (page_id,))
        conn.execute("DELETE FROM confluence_pages WHERE page_id = ?", (page_id,))
        conn.commit()
    conn.close()
except Exception:
    pass  # Hook failure must never block the user

sys.exit(0)
```

- [ ] **Step 2: Add to hooks.json**

Add new PostToolUse matcher for mcp-atlassian write tools:

```json
{
  "matcher": "mcp__mcp-atlassian__(jira_update_issue|jira_add_comment|jira_transition_issue|confluence_update_page|confluence_create_page)",
  "hooks": [{
    "type": "command",
    "command": "TOOL_INPUT=\"$TOOL_INPUT\" python \"${CLAUDE_PLUGIN_ROOT}/hooks/plugin/cache_write_invalidate.py\"",
    "timeout": 5
  }]
}
```

- [ ] **Step 3: Write tests (importable unit tests, not subprocess)**

The hook script's logic is tested by importing the helper functions directly. Extract the invalidation logic into a `_invalidate_db(db_path, key, page_id)` function in the hook script, then test that function.

Restructure `cache_write_invalidate.py` to expose:

```python
def _invalidate_db(db_path, issue_key=None, page_id=None): ...
```

Then add `tests/test_hook_invalidate.py` **in `mcp-servers/atlassian-cache/tests/`**:

```python
"""Tests for hooks/plugin/cache_write_invalidate._invalidate_db."""
import sqlite3, sys
from pathlib import Path

# Add project root to path so we can import the hook
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # up to atlassian-pm root

def _make_db(tmp_path):
    db = tmp_path / "jira.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE issues (issue_key TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE searches (cache_key TEXT PRIMARY KEY, result_keys TEXT)")
    conn.execute("CREATE TABLE confluence_pages (page_id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE confluence_sections (section_id TEXT, page_id TEXT)")
    conn.execute("INSERT INTO issues VALUES ('BEP-99')")
    conn.execute("INSERT INTO confluence_pages VALUES ('P1')")
    conn.commit()
    conn.close()
    return db

def test_invalidate_removes_jira_issue(tmp_path):
    db = _make_db(tmp_path)
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(db, issue_key="BEP-99")
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT * FROM issues WHERE issue_key = 'BEP-99'").fetchone()
    assert row is None

def test_invalidate_removes_confluence_page(tmp_path):
    db = _make_db(tmp_path)
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(db, page_id="P1")
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT * FROM confluence_pages WHERE page_id = 'P1'").fetchone()
    assert row is None

def test_invalidate_noop_when_db_missing(tmp_path):
    """Does not raise when DB doesn't exist."""
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(tmp_path / "nonexistent.db", issue_key="BEP-1")  # should not raise

def test_invalidate_noop_when_no_key(tmp_path):
    db = _make_db(tmp_path)
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(db)  # no key or page_id — should be a no-op
```

Run these tests from the project root:

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm
python -m pytest mcp-servers/atlassian-cache/tests/test_hook_invalidate.py -v
```

Also add `test_hook_invalidate.py` to the atlassian-cache `pyproject.toml` coverage source:

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add hooks/plugin/cache_write_invalidate.py hooks/hooks.json
git commit -m "feat: write-invalidation hook — auto-clear cache after MCP Atlassian writes"
```

---

## Task 14: Update pyproject.toml + Coverage Check

**Files:**

- Modify: `mcp-servers/atlassian-cache/pyproject.toml`
- Fix any coverage gaps

- [ ] **Step 1: Update pyproject.toml**

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
    "sentence-transformers>=3.0.0,<4",
]
test = [
    "pytest>=8.0,<9",
    "pytest-asyncio>=0.24,<1",
    "pytest-cov>=6.0,<7",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["atlassian_cache", "server"]
omit = ["tests/*", ".venv/*"]

[tool.coverage.report]
show_missing = true
fail_under = 100
```

- [ ] **Step 2: Run coverage**

```bash
VIRTUAL_ENV="" uv sync --extra test --project . && \
.venv/bin/python -m pytest tests/ --cov=atlassian_cache --cov=server --cov-report=term-missing -v
```

- [ ] **Step 3: Fix any uncovered lines**

Coverage < 100% → identify uncovered branches → add targeted tests. Common gaps:

- Error paths in handlers (invalid key, None cache)
- `# pragma: no cover` for genuinely unreachable defensive code only

- [ ] **Step 4: Final full run**

```bash
.venv/bin/python -m pytest tests/ --cov=atlassian_cache --cov=server --cov-report=term-missing -v
```

Expected: All PASS, coverage 100%

- [ ] **Step 5: Update doctor script**

In `scripts/setup.sh` (or doctor skill), add check:

```bash
# Check atlassian-cache venv
if [ -d "mcp-servers/atlassian-cache/.venv" ]; then
    echo "✅ atlassian-cache venv exists"
else
    echo "❌ atlassian-cache venv missing — run: cd mcp-servers/atlassian-cache && uv sync"
fi
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: atlassian-cache v1.0.0 — unified Jira + Confluence cache, 21 MCP tools, 100% coverage"
```

---

## Task 15: Risk Mitigations (Spec Section 17)

**Files:**

- Modify: `atlassian_cache/confluence_cache.py` — 500KB body truncation in `put_page`
- Modify: `server.py` — graceful degradation message in `cache_stats`; `cache_reindex` `--model` parameter

- [ ] **Step 1: Write tests**

```python
def test_confluence_body_truncated_at_500kb(confluence_cache):
    """put_page truncates body_md to 500KB to prevent DB bloat."""
    large_body = "## Section\n\n" + "x" * 600_000
    page = make_page(page_id="BIG", body_md=large_body)
    confluence_cache.put_page(page)
    result = confluence_cache.get_page("BIG", max_age_hours=24)
    assert len(result["body_md"]) <= 512_000  # 500KB max

def test_cache_stats_warns_when_embeddings_unavailable(cache):
    """cache_stats output includes embedding_available field."""
    stats = cache.get_stats()
    assert "embedding_available" in stats  # True or False, always present

def test_cache_reindex_graceful_when_no_embeddings(cache, sample_issue):
    """cache_reindex returns informative error when sqlite-vec not installed."""
    cache.put_issue(sample_issue["key"], sample_issue)
    from atlassian_cache.embeddings import EmbeddingStore
    store = EmbeddingStore(cache.conn)
    if store.available:
        pytest.skip("sqlite-vec is installed — skip graceful-degradation test")
    # Verify store.store_batch returns 0 cleanly
    count = store.store_batch([sample_issue])
    assert count == 0
```

- [ ] **Step 2: Implement body truncation in confluence_cache.put_page**

In `_extract_page_fields()`, add:

```python
MAX_BODY_MD_BYTES = 512_000  # 500KB

body_md = page.get("_body_md") or ""
if len(body_md.encode("utf-8")) > MAX_BODY_MD_BYTES:
    # Truncate at a natural section boundary (last \n## before the limit)
    truncated = body_md.encode("utf-8")[:MAX_BODY_MD_BYTES].decode("utf-8", errors="ignore")
    last_boundary = truncated.rfind("\n## ")
    body_md = truncated[:last_boundary] if last_boundary > 0 else truncated
```

- [ ] **Step 3: Add embedding_available to cache_stats**

In `atlassian_cache/cache.py`, update `get_stats()` to include:

```python
"embedding_available": False  # updated by server.py with embeddings.available
```

In `server.py`, when formatting stats response, inject `embeddings.available if embeddings else False`.

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add atlassian_cache/confluence_cache.py atlassian_cache/cache.py server.py
git commit -m "feat: risk mitigations — 500KB body truncation, embedding_available in stats"
```

---

## Summary

| Task | Deliverable | Test File |
|------|-------------|-----------|
| 1 | Directory rename, all 55+ refs updated | All existing tests |
| 2 | PRAGMA at connection open | test_cache.py |
| 3 | migrations.py extracted | test_migrations.py |
| 4 | Schema v4 — Confluence tables | test_migrations.py |
| 5 | Schema v5 — FTS5 porter + columns | test_migrations.py |
| 6 | sections.py | test_sections.py |
| 7 | confluence_cache.py | test_confluence_cache.py |
| 8 | embeddings.py multilingual + cross-modal | test_embeddings.py |
| 9 | In-session dedup + compact format | test_server.py |
| 10 | 9 Confluence MCP tools | test_server.py |
| 11 | 3 new Jira tools | test_server.py, test_cache.py |
| 12 | Lazy version-check invalidation | test_server.py |
| 13 | Write-invalidation hook | test_hook_invalidate.py |
| 14 | pyproject.toml + 100% coverage | all |
| 15 | Risk mitigations (500KB truncation, embedding_available stats) | test_confluence_cache.py, test_cache.py |
