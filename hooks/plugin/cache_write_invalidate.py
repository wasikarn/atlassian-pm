#!/usr/bin/env python3
"""PostToolUse hook: auto-invalidate atlassian-cache after any MCP write.

Reads TOOL_INPUT env var (JSON), extracts issue_key or page_id,
calls cache_invalidate via the cache DB directly (no MCP round-trip).
"""
import json
import os
import sys
from pathlib import Path


def _invalidate_db(db_path, issue_key=None, page_id=None):
    """Invalidate cache entries. No-op if db doesn't exist or no key given."""
    if not issue_key and not page_id:
        return
    db_path = Path(db_path)
    if not db_path.exists():
        return
    import sqlite3
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        if issue_key:
            conn.execute("DELETE FROM issues WHERE issue_key = ?", (issue_key,))
            conn.execute("DELETE FROM searches WHERE result_keys LIKE ?", (f'%"{issue_key}"%',))
            conn.commit()
        if page_id:
            conn.execute("DELETE FROM confluence_sections WHERE page_id = ?", (page_id,))
            conn.execute("DELETE FROM confluence_pages WHERE page_id = ?", (page_id,))
            conn.commit()
        conn.close()
    except Exception:
        pass  # Hook failure must never block the user


if __name__ == "__main__":
    # Resolve DB path same way as server.py
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
    db_path = (
        Path(os.path.abspath(plugin_data)) if plugin_data else Path.home() / ".cache" / "atlassian-pm"
    ) / "atlassian.db"

    tool_input = os.environ.get("TOOL_INPUT", "{}")
    try:
        inp = json.loads(tool_input)
    except json.JSONDecodeError:
        sys.exit(0)

    # Extract what to invalidate
    key = inp.get("issue_key") or inp.get("issueKey")
    page_id = inp.get("id") or inp.get("pageId")

    _invalidate_db(db_path, issue_key=key, page_id=page_id)
    sys.exit(0)
