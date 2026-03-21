"""Semantic similarity search using sqlite-vec and sentence-transformers.

Provides vector embeddings for Jira issues, enabling "find similar issues"
queries beyond keyword matching. Uses all-MiniLM-L6-v2 (384-dim, ~80MB).

Usage:
    from lib.embeddings import EmbeddingStore

    store = EmbeddingStore(conn)  # Reuses JiraCache's SQLite connection
    store.store_embedding("{{PROJECT_KEY}}-123", "coupon collection API endpoint")
    similar = store.find_similar("coupon payment flow", limit=5)
"""

import logging
import sqlite3
import struct
import threading
from typing import Any

from .cache import extract_adf_text

logger = logging.getLogger(__name__)

# Lazy-loaded globals
_model = None
_vec_loaded = False


def _load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec extension into connection.

    Returns:
        True if loaded successfully, False if not available.
    """
    global _vec_loaded
    if _vec_loaded:
        return True

    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)
        _vec_loaded = True
        logger.debug("sqlite-vec extension loaded")
        return True
    except (ImportError, AttributeError, sqlite3.OperationalError) as e:
        logger.warning(
            "sqlite-vec not available: %s — run `uv sync --extra embeddings` to enable semantic search", e
        )
        return False


def _get_model() -> Any:
    """Lazy-load sentence-transformers model.

    Returns:
        SentenceTransformer model instance.
    """
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded embedding model: all-MiniLM-L6-v2")
        return _model
    except ImportError:
        logger.error("sentence-transformers not installed")
        raise


def _serialize_f32(vec: list[float]) -> bytes:
    """Serialize float vector to bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


EMBEDDINGS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS issue_embeddings USING vec0(
    issue_key TEXT PRIMARY KEY,
    embedding float[384]
);
"""


def embedding_text(issue: dict) -> str:
    """Extract text suitable for embedding from an issue dict."""
    f = issue.get("fields", {})
    summary = f.get("summary", "")
    desc_raw = f.get("description")
    desc = ""
    if isinstance(desc_raw, str):
        desc = desc_raw[:500]
    elif isinstance(desc_raw, dict):
        desc = (extract_adf_text(desc_raw) or "")[:500]
    return f"{summary} {desc}".strip()[:500]


class EmbeddingStore:
    """Vector embedding store for semantic issue search.

    Wraps sqlite-vec virtual table for storing and querying
    384-dimensional embeddings from sentence-transformers.

    Attributes:
        conn: SQLite connection (shared with JiraCache).
        available: Whether sqlite-vec is loaded and ready.
        _lock: Shared JiraCache write lock; prevents concurrent SQLite writes.
    """

    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock | None = None) -> None:
        self.conn = conn
        # C3: Accept shared JiraCache._lock to serialize SQLite writes across both classes.
        # Falls back to a private lock when used standalone (e.g. tests).
        self._lock = lock if lock is not None else threading.Lock()
        self.available = _load_sqlite_vec(conn)
        if self.available:
            self._init_schema()

    def _init_schema(self) -> None:
        """Create vec0 virtual table if not exists."""
        try:
            self.conn.executescript(EMBEDDINGS_SCHEMA)
            self.conn.commit()
            logger.debug("Embeddings schema initialized")
        except sqlite3.OperationalError as e:
            if "already exists" not in str(e):
                logger.warning("Embeddings schema error: %s", e)
                self.available = False

    def generate_embedding(self, text: str) -> list[float]:
        """Generate 384-dim embedding from text.

        Args:
            text: Input text (summary + description excerpt)

        Returns:
            384-dimensional float vector.
        """
        model = _get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """P1-C: Batch encode multiple texts in one call.

        Uses sentence-transformers batch encoding for ~5-10x speedup
        over sequential encode calls.

        Args:
            texts: List of input texts

        Returns:
            List of 384-dimensional float vectors.
        """
        if not texts:
            return []
        model = _get_model()
        embeddings = model.encode(texts, batch_size=32, normalize_embeddings=True)
        return [e.tolist() for e in embeddings]

    def store_embedding(self, issue_key: str, text: str) -> bool:
        """Generate and store embedding for an issue.

        Args:
            issue_key: Jira issue key (e.g., '{{PROJECT_KEY}}-123')
            text: Text to embed (typically summary + description)

        Returns:
            True if stored, False if embeddings not available.
        """
        if not self.available:
            return False

        try:
            vec = self.generate_embedding(text)
            with self._lock:
                self.conn.execute(
                    "INSERT OR REPLACE INTO issue_embeddings (issue_key, embedding) VALUES (?, ?)",
                    (issue_key, _serialize_f32(vec)),
                )
                self.conn.commit()
            logger.debug("Stored embedding for %s", issue_key)
            return True
        except Exception as e:
            logger.error("Failed to store embedding for %s: %s", issue_key, e)
            return False

    def find_similar(
        self,
        query: str,
        limit: int = 5,
        exclude_keys: list[str] | None = None,
    ) -> list[dict]:
        """Find issues semantically similar to query text.

        Args:
            query: Search text
            limit: Maximum results
            exclude_keys: Issue keys to exclude from results

        Returns:
            List of {issue_key, distance} dicts, sorted by similarity.
        """
        if not self.available:
            return []

        try:
            vec = self.generate_embedding(query)
            rows = self.conn.execute(
                """SELECT issue_key, distance
                FROM issue_embeddings
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT ?""",
                (_serialize_f32(vec), limit + len(exclude_keys or [])),
            ).fetchall()

            results = []
            excluded = set(exclude_keys or [])
            for row in rows:
                if row[0] not in excluded and len(results) < limit:
                    results.append(
                        {
                            "issue_key": row[0],
                            "distance": round(row[1], 4),
                        }
                    )

            return results
        except Exception as e:
            logger.error("Similarity search failed: %s", e)
            return []

    def store_batch(self, issues: list[dict]) -> int:
        """P1-C: Batch store embeddings using batch encoding.

        Collects all texts first, encodes in one batch call,
        then stores with executemany + single commit.

        Args:
            issues: List of issue dicts from Jira API

        Returns:
            Number of embeddings stored.
        """
        if not self.available:
            return 0

        # Phase 1: Collect texts
        items: list[tuple[str, str]] = []  # (key, text)
        for issue in issues:
            key = issue.get("key", "")
            text = embedding_text(issue)
            if key and text:
                items.append((key, text))

        if not items:
            return 0

        # Phase 2: Batch encode
        try:
            texts = [text for _, text in items]
            vectors = self.generate_embeddings_batch(texts)
        except Exception as e:
            logger.error("Batch embedding encode failed: %s", e)
            return 0

        # Phase 3: Batch store with executemany + single commit
        count = 0
        try:
            rows = [
                (key, _serialize_f32(vec))
                for (key, _), vec in zip(items, vectors, strict=True)
            ]
            with self._lock:
                self.conn.executemany(
                    "INSERT OR REPLACE INTO issue_embeddings (issue_key, embedding) VALUES (?, ?)",
                    rows,
                )
                count = len(rows)
                self.conn.commit()
            logger.info("Batch stored %d embeddings (single commit)", count)
        except Exception as e:
            logger.error("Batch embedding store failed: %s", e)

        return count

    def remove_embedding(self, issue_key: str) -> bool:
        """Remove embedding for an issue."""
        if not self.available:
            return False

        try:
            with self._lock:
                self.conn.execute(
                    "DELETE FROM issue_embeddings WHERE issue_key = ?",
                    (issue_key,),
                )
                self.conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to remove embedding %s: %s", issue_key, e)
            return False

    def count(self) -> int:
        """Count stored embeddings."""
        if not self.available:
            return 0
        try:
            row = self.conn.execute("SELECT COUNT(*) FROM issue_embeddings").fetchone()
            return row[0] if row else 0
        except Exception:
            return 0
