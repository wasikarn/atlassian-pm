#!/usr/bin/env python3
"""Direct SQLite cache invalidation utility for hooks.

Removes Jira issues and Confluence pages from the atlassian-cache SQLite DB
without going through the MCP server. Used by HR6 hooks to ensure cache
consistency immediately after write operations.

Usage:
    from hooks.plugin.cache_write_invalidate import _invalidate_db
    _invalidate_db(db_path, issue_key="TP-100")
    _invalidate_db(db_path, page_id="12345")
"""

import json
import sqlite3
from pathlib import Path


def _invalidate_db(
    db_path: Path | str,
    *,
    issue_key: str | None = None,
    page_id: str | None = None,
) -> None:
    """Remove a Jira issue or Confluence page from the cache DB.

    No-op when:
    - DB file does not exist
    - Neither issue_key nor page_id is provided

    Search rows are evicted only when they contain the exact issue_key
    (prevents TP-1 from evicting rows that contain only TP-10).

    Args:
        db_path: Path to atlassian.db SQLite file.
        issue_key: Jira issue key to remove (e.g. "TP-100").
        page_id: Confluence page ID to remove (e.g. "12345").
    """
    if not issue_key and not page_id:
        return

    db_path = Path(db_path)
    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    try:
        if issue_key:
            conn.execute("DELETE FROM issues WHERE issue_key = ?", (issue_key,))
            # Evict searches that contain this exact key using JSON parsing
            rows = conn.execute("SELECT cache_key, result_keys FROM searches").fetchall()
            to_delete = []
            for cache_key, result_keys_json in rows:
                try:
                    keys = json.loads(result_keys_json)
                    if issue_key in keys:
                        to_delete.append(cache_key)
                except (json.JSONDecodeError, TypeError):
                    pass
            for cache_key in to_delete:
                conn.execute("DELETE FROM searches WHERE cache_key = ?", (cache_key,))

        if page_id:
            conn.execute("DELETE FROM confluence_pages WHERE page_id = ?", (page_id,))
            conn.execute("DELETE FROM confluence_sections WHERE page_id = ?", (page_id,))

        conn.commit()
    finally:
        conn.close()
