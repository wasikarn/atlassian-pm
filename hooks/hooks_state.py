"""Shared session state for Claude hooks.

Replaces JSON-based state with SQLite in WAL mode to eliminate lock contention
and prevent "Levitating..." hangs during stop-hooks.

State is stored in /tmp/claude-hooks-state/{session_id}.db
"""

import sqlite3
import json
import os
import sys
import time
import functools
import hashlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_project_config

STATE_DIR = Path("/tmp/claude-hooks-state")
_STATE_DIR_STR = str(STATE_DIR)  # Kept for backward compatibility with tests

STATE_EXPIRY_SECONDS = 3600  # 1 hour

def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)

def _get_db_path(session_id: str) -> Path:
    return STATE_DIR / f"{session_id or 'default'}.db"

def _get_connection(session_id: str, fast_mode: bool = False) -> sqlite3.Connection:
    """Creates a connection to the SQLite state DB with WAL mode enabled.

    Args:
        session_id: Session identifier
        fast_mode: If True, use shorter timeout (1s vs 5s), skip JSON migration,
                   and skip memory-mapped I/O optimizations. Use for stop hooks
                   where speed is critical and old data migration is not needed.
                   Note: fast_mode still creates schema tables as they are required.
    """
    _ensure_state_dir()
    db_path = _get_db_path(session_id)

    # Fast mode: shorter timeout for stop hooks
    timeout = 1.0 if fast_mode else 5.0
    conn = sqlite3.connect(str(db_path), timeout=timeout)

    # WAL mode allows concurrent reads and writes without blocking
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    if not fast_mode:
        # Full optimization (for regular operations)
        conn.execute("PRAGMA mmap_size = 268435456;")
        conn.execute("PRAGMA cache_size = -64000;")

    # Initialize schema (always needed)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT,
            ts REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS state_deltas (
            key TEXT,
            delta TEXT,
            ts REAL,
            PRIMARY KEY (key, ts)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bloom_filter (
            session_id TEXT PRIMARY KEY,
            bitset BLOB
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hr5_pending (
            child TEXT,
            parent TEXT,
            ts REAL,
            PRIMARY KEY (child, parent)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS known_subtasks (
            key TEXT PRIMARY KEY
        )
    """)

    # Skip migration in fast mode (stop hooks don't need old JSON data)
    if not fast_mode:
        _migrate_from_json(session_id, conn)

    return conn

def _migrate_from_json(session_id: str, conn: sqlite3.Connection) -> None:
    """Migrates data from old .json state file to SQLite."""
    json_file = STATE_DIR / f"{session_id or 'default'}.json"
    if not json_file.exists():
        return

    try:
        state = json.loads(json_file.read_text())

        # Get Bloom Filter for current session to update it during migration
        conn_bf = _get_connection(session_id)
        bf = _get_bloom_filter(session_id, conn_bf)

        # Migrate global state
        for key, val in state.items():
            if isinstance(val, dict) and 'value' in val:
                conn.execute(
                    "INSERT OR REPLACE INTO state (key, value, ts) VALUES (?, ?, ?)",
                    (key, json.dumps(val['value']), val.get('ts', time.time()))
                )
                bf.add(key)
            elif key == "hr6_pending":
                for k in val:
                    hr6_add_pending(session_id, k)
            elif key == "hr5_pending":
                for p in val:
                    if isinstance(p, dict):
                        conn.execute(
                            "INSERT OR REPLACE INTO hr5_pending (child, parent, ts) VALUES (?, ?, ?)",
                            (p['child'], p['parent'], p.get('ts', time.time()))
                        )
            elif key == "hr5_known_subtasks":
                for k in val:
                    conn.execute("INSERT OR REPLACE INTO known_subtasks (key) VALUES (?)", (k,))

        _save_bloom_filter(session_id, conn_bf, bf)
        conn_bf.close()

        # Archive old json file
        json_file.rename(json_file.with_suffix(".json.bak"))
    except Exception as e:
        # Log migration failure but don't crash the hook
        print(f"Migration error: {e}", file=sys.stderr)

# ── Advanced Optimizations ────────────────────────────────

class SimpleBloomFilter:
    """Simple Bloom Filter for fast key existence checks.
    Optimized for short-lived CLI processes: persisted as bitset in DB.
    """
    def __init__(self, size=1024 * 8):  # 8Kb bitset
        self.size = size
        self.bitset = bytearray(size // 8)

    def _hashes(self, key: str):
        h1 = int(hashlib.md5(key.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha1(key.encode()).hexdigest(), 16)
        for i in range(3):
            yield (h1 + i * h2) % self.size

    def add(self, key: str):
        for h in self._hashes(key):
            self.bitset[h // 8] |= (1 << (h % 8))

    def exists(self, key: str) -> bool:
        for h in self._hashes(key):
            if not (self.bitset[h // 8] & (1 << (h % 8))):
                return False
        return True

    def to_bytes(self) -> bytes:
        return bytes(self.bitset)

    @classmethod
    def from_bytes(cls, data: bytes):
        bf = cls(len(data) * 8)
        bf.bitset = bytearray(data)
        return bf

def _get_bloom_filter(session_id: str, conn: sqlite3.Connection) -> SimpleBloomFilter:
    cursor = conn.execute("SELECT bitset FROM bloom_filter WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    if row:
        return SimpleBloomFilter.from_bytes(row[0])
    return SimpleBloomFilter()

def _save_bloom_filter(session_id: str, conn: sqlite3.Connection, bf: SimpleBloomFilter):
    conn.execute("INSERT OR REPLACE INTO bloom_filter (session_id, bitset) VALUES (?, ?)",
                 (session_id, bf.to_bytes()))

def merge_deltas(base_value: Any, deltas: list[dict]) -> Any:
    """Merges a base value with a sequence of JSON patches (deltas)."""
    import copy
    current = copy.deepcopy(base_value)
    for delta in deltas:
        patch = delta.get("patch")
        if isinstance(current, dict) and isinstance(patch, dict):
            current.update(patch)
        elif isinstance(current, list) and isinstance(patch, list):
            # Simple append for lists; in a real system this would be more complex
            current.extend(patch)
        else:
            current = patch
    return current

# ── Generic State API ──────────────────────────────────

@functools.lru_cache(maxsize=128)
def get_state(session_id: str, key: str) -> Any | None:
    """Get a state value set by set_state. Returns None if expired.
    L1 Cache: Cached for the duration of the process.
    """
    conn = _get_connection(session_id)
    try:
        # Probabilistic check: Skip DB if Bloom Filter says it's not there
        bf = _get_bloom_filter(session_id, conn)
        if not bf.exists(key):
            return None

        cursor = conn.execute("SELECT value, ts FROM state WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            value, ts = row
            if time.time() - ts > STATE_EXPIRY_SECONDS:
                return None

            # Resolve deltas if any exist
            base_val = json.loads(value)
            cursor_deltas = conn.execute("SELECT delta FROM state_deltas WHERE key = ? ORDER BY ts ASC", (key,))
            deltas = [json.loads(d[0]) for d in cursor_deltas.fetchall()]

            if deltas:
                return merge_deltas(base_val, deltas)
            return base_val
        return None
    finally:
        conn.close()

def set_state(session_id: str, key: str, value: Any) -> None:
    """Set a state value with automatic timestamp tracking and delta support."""
    # Invalidate L1 cache for this key
    get_state.cache_clear()
    conn = _get_connection(session_id)
    try:
        # Delta Tracking: If value is a large dict/list, store as delta if base exists
        cursor = conn.execute("SELECT value FROM state WHERE key = ?", (key,))
        row = cursor.fetchone()

        is_large = isinstance(value, (dict, list)) and len(str(value)) > 1024

        if row and is_large:
            base_val = json.loads(row[0])
            # Calculate simple delta (for dicts)
            if isinstance(value, dict) and isinstance(base_val, dict):
                diff = {k: v for k, v in value.items() if v != base_val.get(k)}
                if diff:
                    conn.execute("INSERT INTO state_deltas (key, delta, ts) VALUES (?, ?, ?)",
                                 (key, json.dumps({"patch": diff}), time.time()))
                    conn.commit()
                    # We don't update the base state every time to keep it stable
                    # but we could optionally update it if deltas get too long
                    return

        # Full write (base state)
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value, ts) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time())
        )

        # Update Bloom Filter
        bf = _get_bloom_filter(session_id, conn)
        bf.add(key)
        _save_bloom_filter(session_id, conn, bf)

        # Clear old deltas when base is reset
        conn.execute("DELETE FROM state_deltas WHERE key = ?", (key,))

        conn.commit()
    finally:
        conn.close()

def cleanup_stale_state(session_id: str) -> None:
    """Remove state entries older than STATE_EXPIRY_SECONDS."""
    conn = _get_connection(session_id)
    try:
        now = time.time()
        conn.execute("DELETE FROM state WHERE ts < ?", (now - STATE_EXPIRY_SECONDS,))
        conn.execute("DELETE FROM hr5_pending WHERE ts < ?", (now - STATE_EXPIRY_SECONDS,))
        conn.commit()
    finally:
        conn.close()

# ── HR6: Cache invalidation tracking ──────────────────

def hr6_add_pending(session_id: str, key: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS hr6_pending (key TEXT PRIMARY KEY)")
        conn.execute("INSERT OR REPLACE INTO hr6_pending (key) VALUES (?)", (key,))
        conn.commit()

        # Update Bloom Filter for keys in hr6_pending
        bf = _get_bloom_filter(session_id, conn)
        bf.add(f"hr6_pending:{key}")
        _save_bloom_filter(session_id, conn, bf)
    finally:
        conn.close()

def hr6_remove_pending(session_id: str, key: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("DELETE FROM hr6_pending WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()

def hr6_get_pending(session_id: str, fast_mode: bool = False) -> set[str]:
    """Get pending HR6 invalidations.

    Args:
        session_id: Session ID
        fast_mode: If True, use optimized path for stop hooks (no migration, cached connection)
    """
    conn = _get_connection(session_id, fast_mode=fast_mode)
    try:
        cursor = conn.execute("SELECT key FROM hr6_pending")
        return set(row[0] for row in cursor.fetchall())
    finally:
        conn.close()

def hr6_clear_all_pending(session_id: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("DELETE FROM hr6_pending")
        conn.commit()
    finally:
        conn.close()

# ── HR7: Sprint lookup tracking ───────────────────────

def hr7_mark_lookup_done(session_id: str) -> None:
    set_state(session_id, "hr7_lookup_done", True)

def hr7_is_lookup_done(session_id: str) -> bool:
    return bool(get_state(session_id, "hr7_lookup_done"))

# ── Search tracking ───────────────────────────────────

def search_mark_done(session_id: str) -> None:
    set_state(session_id, "search_done", True)

def search_is_done(session_id: str) -> bool:
    return bool(get_state(session_id, "search_done"))

# ── HR5: Parent verification tracking ─────────────────

def hr5_add_pending(session_id: str, child_key: str, parent_key: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO hr5_pending (child, parent, ts) VALUES (?, ?, ?)",
            (child_key, parent_key, time.time())
        )
        conn.commit()
    finally:
        conn.close()

def hr5_get_pending(session_id: str, fast_mode: bool = False) -> list:
    """Get pending HR5 parent verifications.

    Args:
        session_id: Session ID
        fast_mode: If True, use optimized path for stop hooks (no migration, cached connection)
    """
    conn = _get_connection(session_id, fast_mode=fast_mode)
    try:
        cursor = conn.execute("SELECT child, parent, ts FROM hr5_pending")
        return [{"child": row[0], "parent": row[1], "ts": row[2]} for row in cursor.fetchall()]
    finally:
        conn.close()

def hr5_add_known_subtask(session_id: str, child_key: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("INSERT OR REPLACE INTO known_subtasks (key) VALUES (?)", (child_key,))
        conn.commit()
    finally:
        conn.close()

def hr5_is_known_subtask(session_id: str, issue_key: str) -> bool:
    conn = _get_connection(session_id)
    try:
        cursor = conn.execute("SELECT 1 FROM known_subtasks WHERE key = ?", (issue_key,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def hr5_remove_pending(session_id: str, child_key: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("DELETE FROM hr5_pending WHERE child = ?", (child_key,))
        conn.commit()
    finally:
        conn.close()

# ── Event-AC: Domain Model tracking ──────────────────

def event_set_domain_events(session_id: str, epic_key: str, events: list) -> None:
    set_state(session_id, f"domain_events_{epic_key}", events)

def event_get_all_events(session_id: str) -> list:
    conn = _get_connection(session_id)
    try:
        cursor = conn.execute("SELECT key, value FROM state WHERE key LIKE 'domain_events_%'")
        all_events = []
        for key, value in cursor.fetchall():
            all_events.extend(json.loads(value))
        return list(set(all_events))
    finally:
        conn.close()

# ── VS Integrity: AC coverage tracking ───────────────

def vs_set_story_acs(session_id: str, story_key: str, acs: list) -> None:
    set_state(session_id, f"vs_story_acs_{story_key}", acs)

def vs_add_subtask(session_id: str, story_key: str, subtask_key: str, summary: str) -> None:
    # For VS subtasks, we use a specific key to avoid huge JSON blobs
    # and allow easier querying.
    key = f"vs_subtask_{story_key}_{subtask_key}"
    set_state(session_id, key, {"summary": summary, "story": story_key})

def vs_get_coverage(session_id: str) -> dict:
    conn = _get_connection(session_id)
    try:
        story_acs = {}
        subtasks = {}
        cursor = conn.execute("SELECT key, value FROM state")
        for key, value in cursor.fetchall():
            val = json.loads(value)
            if key.startswith("vs_story_acs_"):
                story_key = key.replace("vs_story_acs_", "")
                story_acs[story_key] = val
            elif key.startswith("vs_subtask_"):
                # key: vs_subtask_{story}_{subtask}
                parts = key.replace("vs_subtask_", "").split("_")
                if len(parts) >= 2:
                    story_key, subtask_key = parts[0], parts[1]
                    if story_key not in subtasks:
                        subtasks[story_key] = []
                    subtasks[story_key].append({"key": subtask_key, "summary": val.get("summary", "")})
        return {"story_acs": story_acs, "subtasks": subtasks}
    finally:
        conn.close()

# ── Cache-prefer: per-issue cache-first tracking ─────

def cache_mark_checked(session_id: str, issue_key: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS cache_checked (key TEXT PRIMARY KEY)")
        conn.execute("INSERT OR REPLACE INTO cache_checked (key) VALUES (?)", (issue_key,))
        conn.commit()
    finally:
        conn.close()

def cache_is_checked(session_id: str, issue_key: str) -> bool:
    conn = _get_connection(session_id)
    try:
        cursor = conn.execute("SELECT 1 FROM cache_checked WHERE key = ?", (issue_key,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

# ── Cache-first warning: per-session warning count ──────────────────

def cache_warning_count(session_id: str) -> int:
    val = get_state(session_id, "cache_warning_count")
    return val if val is not None else 0

def cache_warning_increment(session_id: str) -> None:
    count = cache_warning_count(session_id)
    set_state(session_id, "cache_warning_count", count + 1)

# ── QMD: Usage tracking ─────────────────────────────

def qmd_mark_collection_searched(session_id: str, collection: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS qmd_searched (collection TEXT PRIMARY KEY)")
        conn.execute("INSERT OR REPLACE INTO qmd_searched (collection) VALUES (?)", (collection,))
        conn.commit()
    finally:
        conn.close()

def qmd_is_collection_searched(session_id: str, collection: str) -> bool:
    conn = _get_connection(session_id)
    try:
        cursor = conn.execute("SELECT 1 FROM qmd_searched WHERE collection = ?", (collection,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def qmd_collection_for_path(path: str) -> str | None:
    config = load_project_config()
    for svc in config.get("services", {}).get("tags", []):
        if svc.get("path"):
            resolved = Path(svc["path"]).expanduser()
            if path.startswith(str(resolved)):
                return resolved.name
    return None

# ── Jira write activity tracking ────────────────────────────────────────────

def jira_write_mark_occurred(session_id: str) -> None:
    set_state(session_id, "jira_write_occurred", True)

def jira_write_is_occurred(session_id: str) -> bool:
    return bool(get_state(session_id, "jira_write_occurred"))

# ── Subtask alignment tracking ──────────────────────────────────────────────

def alignment_mark_sprint_suggested(session_id: str, sprint_id: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS alignment_suggested (sprint_id TEXT PRIMARY KEY)")
        conn.execute("INSERT OR REPLACE INTO alignment_suggested (sprint_id) VALUES (?)", (str(sprint_id),))
        conn.commit()
    finally:
        conn.close()

def alignment_is_sprint_suggested(session_id: str, sprint_id: str) -> bool:
    conn = _get_connection(session_id)
    try:
        cursor = conn.execute("SELECT 1 FROM alignment_suggested WHERE sprint_id = ?", (str(sprint_id),))
        return cursor.fetchone() is not None
    finally:
        conn.close()

# ── Sprint risk assessment tracking ─────────────────────────────────────────

def risk_mark_sprint_assessed(session_id: str, sprint_id: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS risk_assessed (sprint_id TEXT PRIMARY KEY)")
        conn.execute("INSERT OR REPLACE INTO risk_assessed (sprint_id) VALUES (?)", (str(sprint_id),))
        conn.commit()
    finally:
        conn.close()

def risk_is_sprint_assessed(session_id: str, sprint_id: str) -> bool:
    conn = _get_connection(session_id)
    try:
        cursor = conn.execute("SELECT 1 FROM risk_assessed WHERE sprint_id = ?", (str(sprint_id),))
        return cursor.fetchone() is not None
    finally:
        conn.close()

# ── Skill checkpoint tracking ────────────────────────────────────────────────

def skill_checkpoint_save(session_id: str, key: str, issue_type: str, parent_key: str | None = None) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS skill_checkpoints (key TEXT PRIMARY KEY, type TEXT, parent TEXT, ts REAL)")
        conn.execute(
            "INSERT OR REPLACE INTO skill_checkpoints (key, type, parent, ts) VALUES (?, ?, ?, ?)",
            (key, issue_type, parent_key, time.time())
        )
        # Maintain subtask limit (last 10)
        if "subtask" in issue_type.lower():
            conn.execute("""
                DELETE FROM skill_checkpoints
                WHERE type LIKE '%subtask%' AND key NOT IN (
                    SELECT key FROM skill_checkpoints
                    WHERE type LIKE '%subtask%'
                    ORDER BY ts DESC LIMIT 10
                )
            """)
        conn.commit()
    finally:
        conn.close()

def skill_checkpoint_get(session_id: str) -> dict:
    conn = _get_connection(session_id)
    try:
        cursor = conn.execute("SELECT key, type, parent, ts FROM skill_checkpoints")
        rows = cursor.fetchall()

        cp = {"subtasks": []}
        for key, itype, parent, ts in rows:
            entry = {"key": key, "type": itype, "ts": ts}
            if parent: entry["parent"] = parent

            if "subtask" in itype.lower():
                cp["subtasks"].append(entry)
            elif "epic" in itype.lower():
                cp["latest_epic"] = entry
            else:
                cp["latest_story"] = entry
        return cp
    finally:
        conn.close()

def skill_checkpoint_clear(session_id: str) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("DELETE FROM skill_checkpoints")
        conn.commit()
    finally:
        conn.close()

def _load() -> dict:
    return load_state()

def _save(state: dict) -> None:
    save_state(state)

def load_state() -> dict:
    """Load global session state (session-id-agnostic convenience wrapper)."""
    conn = _get_connection("default")
    try:
        cursor = conn.execute("SELECT key, value FROM state")
        return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
    finally:
        conn.close()

def save_state(state: dict) -> None:
    """Persist global session state (session-id-agnostic convenience wrapper)."""
    conn = _get_connection("default")
    try:
        for key, value in state.items():
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value, ts) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time())
            )
        conn.commit()
    finally:
        conn.close()

# ── Response size tracking (token usage observability) ───────────────────

def response_size_track(session_id: str, tool: str, chars: int, tokens: int) -> None:
    conn = _get_connection(session_id)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS response_sizes (
                tool TEXT PRIMARY KEY,
                chars INTEGER,
                tokens INTEGER,
                calls INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO response_sizes (tool, chars, tokens, calls)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(tool) DO UPDATE SET
                chars = chars + excluded.chars,
                tokens = tokens + excluded.tokens,
                calls = calls + 1
        """, (tool, chars, tokens))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS response_totals (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                chars INTEGER,
                tokens INTEGER,
                calls INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO response_totals (id, chars, tokens, calls)
            VALUES (1, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                chars = chars + excluded.chars,
                tokens = tokens + excluded.tokens,
                calls = calls + 1
        """, (chars, tokens))

        conn.commit()
    finally:
        conn.close()

def response_size_get_stats(session_id: str) -> dict:
    conn = _get_connection(session_id)
    try:
        totals_row = conn.execute("SELECT chars, tokens, calls FROM response_totals WHERE id = 1").fetchone()
        totals = {"chars": totals_row[0], "tokens": totals_row[1], "calls": totals_row[2]} if totals_row else {"chars": 0, "tokens": 0, "calls": 0}

        by_tool = {}
        cursor = conn.execute("SELECT tool, chars, tokens, calls FROM response_sizes")
        for tool, chars, tokens, calls in cursor.fetchall():
            by_tool[tool] = {"chars": chars, "tokens": tokens, "calls": calls}

        return {"totals": totals, "by_tool": by_tool}
    finally:
        conn.close()
