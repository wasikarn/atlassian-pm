"""UserPromptSubmit hook: pre-fetch issue data from cache when user mentions {{PROJECT_KEY}}-XXX keys.

When the user's prompt contains Jira issue keys (e.g. "ดู {{PROJECT_KEY}}-456" or "update {{PROJECT_KEY}}-123"),
this hook queries the local SQLite cache directly and injects a summary as additionalContext
— before Claude starts processing.

Benefits:
  - Claude has issue context before the first tool call
  - Saves 1-2 MCP round-trips for already-cached issues
  - Works even if Claude would have fetched via cache_get_issue anyway (just faster)

Limits fetched to 5 keys per prompt to avoid token bloat.
Falls back silently if cache DB missing or key not found.

Exit 0 = always allow (never blocks user prompts).
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import inject_context, log_event
from config_loader import load_project_config

_HOOK       = "prompt-issue-prefetch"
CACHE_DB    = Path.home() / ".cache" / "atlassian-pm" / "jira.db"
MAX_KEYS    = 5
MAX_DESC_LEN = 200  # chars of description to include

_cfg        = load_project_config()
PROJECT_KEY = _cfg.get("jira", {}).get("project_key", "")
KEY_RE      = re.compile(rf"\b{re.escape(PROJECT_KEY)}-(\d+)\b", re.I) if PROJECT_KEY else None


def _shorten(text: str | None, n: int = MAX_DESC_LEN) -> str:
    if not text:
        return ""
    text = text.strip()
    return text[:n] + "…" if len(text) > n else text


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    prompt     = data.get("prompt", "")
    session_id = data.get("session_id", "")

    raw_keys = KEY_RE.findall(prompt) if KEY_RE is not None else []
    if not raw_keys:
        sys.exit(0)

    # Deduplicate preserving order, normalise to {{PROJECT_KEY}}-NNN uppercase
    seen: set[str] = set()
    keys: list[str] = []
    for n in raw_keys:
        k = f"{PROJECT_KEY}-{int(n)}"
        if k not in seen:
            seen.add(k)
            keys.append(k)
        if len(keys) >= MAX_KEYS:
            break

    if not CACHE_DB.exists():
        sys.exit(0)

    try:
        conn   = sqlite3.connect(str(CACHE_DB), timeout=2)
        rows   = []
        for key in keys:
            row = conn.execute(
                "SELECT issue_key, summary, status, issue_type, assignee_name, description "
                "FROM issues WHERE issue_key = ?",
                (key,),
            ).fetchone()
            if row:
                rows.append(row)
        conn.close()
    except Exception as e:
        log_event(_HOOK, "ERROR", {"error": str(e), "session_id": session_id})
        sys.exit(0)

    if not rows:
        sys.exit(0)

    lines = ["Pre-fetched from cache (mention in prompt):"]
    for ik, summary, status, itype, assignee, desc in rows:
        line = f"  {ik} [{status or '?'}] ({itype or '?'}) — {summary or '(no summary)'}"
        if assignee:
            line += f" → {assignee}"
        if desc:
            line += f"\n    {_shorten(desc)}"
        lines.append(line)

    missing = [k for k in keys if k not in {r[0] for r in rows}]
    if missing:
        lines.append(f"  Not in cache (will need MCP fetch): {', '.join(missing)}")

    log_event(_HOOK, "PREFETCHED", {
        "keys": [r[0] for r in rows],
        "session_id": session_id,
    })
    inject_context("\n".join(lines), event_name="UserPromptSubmit")


if __name__ == "__main__":
    main()
