"""Semantic similarity search using sqlite-vec and sentence-transformers.

Provides vector embeddings for Jira issues and other entities, enabling
"find similar issues" queries beyond keyword matching.
Uses paraphrase-multilingual-MiniLM-L12-v2 (384-dim, ~470MB) for multilingual
support across Thai, English, and other languages.

Usage:
    from atlassian_cache.embeddings import EmbeddingStore

    store = EmbeddingStore(conn)  # Reuses AtlassianCache's SQLite connection
    store.store_embedding("{{PROJECT_KEY}}-123", "coupon collection API endpoint")
    similar = store.find_similar("coupon payment flow", limit=5)
"""

from __future__ import annotations

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
_model_loaded = False  # Track if sentence-transformers import succeeded

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# SentenceTransformer is NOT imported at module level to avoid ~500MB cold start.
# It will be imported lazily in _get_model() only when semantic search is used.


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

    Imports sentence-transformers ONLY when semantic search is used,
    avoiding ~500MB cold start penalty at server startup.

    Returns:
        SentenceTransformer model instance.
    """
    global _model, _model_loaded
    if _model is not None:
        return _model

    # Lazy import: only load sentence-transformers when actually needed
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("sentence-transformers not installed")
        raise ImportError("sentence-transformers not installed — run `uv sync --extra embeddings`")

    _model = SentenceTransformer(MODEL_NAME)
    _model_loaded = True
    logger.info("Loaded embedding model: %s", MODEL_NAME)
    return _model


def _serialize_f32(vec: list[float]) -> bytes:
    """Serialize float vector to bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


EMBEDDINGS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT,
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
        conn: SQLite connection (shared with AtlassianCache).
        available: Whether sqlite-vec is loaded and ready.
        _lock: Shared AtlassianCache write lock; prevents concurrent SQLite writes.
    """

    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock | None = None) -> None:
        self.conn = conn
        # C3: Accept shared AtlassianCache._lock to serialize SQLite writes across both classes.
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

    def store_embedding(self, entity_id: str, text: str, entity_type: str = "jira") -> bool:
        """Generate and store embedding for an entity.

        Args:
            entity_id: Unique entity identifier (e.g., Jira issue key '{{PROJECT_KEY}}-123')
            text: Text to embed (typically summary + description)
            entity_type: Entity type for cross-modal filtering (default: "jira")

        Returns:
            True if stored, False if embeddings not available.
        """
        if not self.available:
            return False

        try:
            vec = self.generate_embedding(text)
            with self._lock:
                self.conn.execute(
                    "INSERT OR REPLACE INTO embeddings (entity_id, entity_type, embedding) VALUES (?, ?, ?)",
                    (entity_id, entity_type, _serialize_f32(vec)),
                )
                self.conn.commit()
            logger.debug("Stored embedding for %s (type=%s)", entity_id, entity_type)
            return True
        except Exception as e:
            logger.error("Failed to store embedding for %s: %s", entity_id, e)
            return False

    def find_similar(
        self,
        query: str,
        limit: int = 5,
        exclude_keys: list[str] | None = None,
        entity_type: str | None = None,
    ) -> list[dict]:
        """Find entities semantically similar to query text.

        Args:
            query: Search text
            limit: Maximum results
            exclude_keys: Entity IDs to exclude from results
            entity_type: If set, filter results to this entity type only (cross-modal filter)

        Returns:
            List of {entity_id, entity_type, distance} dicts, sorted by similarity.
        """
        if not self.available:
            return []

        try:
            vec = self.generate_embedding(query)
            type_clause = "AND entity_type = ?" if entity_type else ""
            params: list[Any] = [_serialize_f32(vec)]
            if entity_type:
                params.append(entity_type)
            params.append(limit + len(exclude_keys or []))

            rows = self.conn.execute(
                f"""SELECT entity_id, entity_type, distance
                FROM embeddings
                WHERE embedding MATCH ?
                {type_clause}
                ORDER BY distance
                LIMIT ?""",
                params,
            ).fetchall()

            results = []
            excluded = set(exclude_keys or [])
            for row in rows:
                if row[0] not in excluded and len(results) < limit:
                    results.append(
                        {
                            "entity_id": row[0],
                            "entity_type": row[1],
                            "distance": round(row[2], 4),
                        }
                    )

            return results
        except Exception as e:
            logger.error("Similarity search failed: %s", e)
            return []

    def find_similar_by_embedding(
        self,
        embedding: list[float],
        limit: int = 5,
        exclude_keys: list[str] | None = None,
        entity_type: str | None = None,
    ) -> list[dict]:
        """Find entities similar to a pre-computed embedding vector.

        Avoids a redundant model.encode() call when the caller already holds the vector.
        Same return format as find_similar.
        """
        if not self.available:
            return []

        try:
            type_clause = "AND entity_type = ?" if entity_type else ""
            params: list[Any] = [_serialize_f32(embedding)]
            if entity_type:
                params.append(entity_type)
            params.append(limit + len(exclude_keys or []))

            rows = self.conn.execute(
                f"""SELECT entity_id, entity_type, distance
                FROM embeddings
                WHERE embedding MATCH ?
                {type_clause}
                ORDER BY distance
                LIMIT ?""",
                params,
            ).fetchall()

            results = []
            excluded = set(exclude_keys or [])
            for row in rows:
                if row[0] not in excluded and len(results) < limit:
                    results.append(
                        {
                            "entity_id": row[0],
                            "entity_type": row[1],
                            "distance": round(row[2], 4),
                        }
                    )
            return results
        except Exception as e:
            logger.error("Similarity search (by embedding) failed: %s", e)
            return []

    def store_batch_entities(self, entities: list[tuple[str, str, str]]) -> int:
        """Batch store embeddings for generic (non-issue) entities.

        Args:
            entities: List of (entity_id, text, entity_type) tuples.

        Returns:
            Number of embeddings stored.
        """
        if not self.available or not entities:
            return 0

        # Filter empty texts
        valid = [(eid, text, etype) for eid, text, etype in entities if text.strip()]
        if not valid:
            return 0

        try:
            texts = [text for _, text, _ in valid]
            vectors = self.generate_embeddings_batch(texts)
        except Exception as e:
            logger.error("Batch entity embedding encode failed: %s", e)
            return 0

        count = 0
        try:
            rows = [
                (eid, etype, _serialize_f32(vec))
                for (eid, _, etype), vec in zip(valid, vectors, strict=True)
            ]
            with self._lock:
                self.conn.executemany(
                    "INSERT OR REPLACE INTO embeddings (entity_id, entity_type, embedding) VALUES (?, ?, ?)",
                    rows,
                )
                count = len(rows)
                self.conn.commit()
            logger.info("Batch stored %d entity embeddings (single commit)", count)
        except Exception as e:
            logger.error("Batch entity embedding store failed: %s", e)

        return count

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
                (key, "jira", _serialize_f32(vec))
                for (key, _), vec in zip(items, vectors, strict=True)
            ]
            with self._lock:
                self.conn.executemany(
                    "INSERT OR REPLACE INTO embeddings (entity_id, entity_type, embedding) VALUES (?, ?, ?)",
                    rows,
                )
                count = len(rows)
                self.conn.commit()
            logger.info("Batch stored %d embeddings (single commit)", count)
        except Exception as e:
            logger.error("Batch embedding store failed: %s", e)

        return count

    def remove_embedding(self, entity_id: str) -> bool:
        """Remove embedding for an entity."""
        if not self.available:
            return False

        try:
            with self._lock:
                self.conn.execute(
                    "DELETE FROM embeddings WHERE entity_id = ?",
                    (entity_id,),
                )
                self.conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to remove embedding %s: %s", entity_id, e)
            return False

    def count(self) -> int:
        """Count stored embeddings."""
        if not self.available:
            return 0
        try:
            row = self.conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
            return row[0] if row else 0
        except Exception:
            return 0
