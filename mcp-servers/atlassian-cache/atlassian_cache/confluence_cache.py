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
import json
import logging
import re
import threading
import time
from typing import Any

from .sections import SectionData, diff_sections

logger = logging.getLogger(__name__)


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
        result = dict(row)
        result["id"] = result["page_id"]  # alias for API compatibility
        return result

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
        safe_q = re.sub(r"[^a-zA-Z0-9\u0E00-\u0E7F\s]", " ", query).strip()
        if not safe_q:
            return []
        try:
            rows = self.conn.execute("""
                SELECT p.page_id, p.title,
                       bm25(confluence_fts, 10.0, 5.0, 2.0) AS rank
                FROM confluence_fts
                JOIN confluence_pages p ON p.rowid = confluence_fts.rowid
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
