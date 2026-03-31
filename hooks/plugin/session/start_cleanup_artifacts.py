#!/usr/bin/env python3
"""SessionStart cleanup: remove stale artifacts and trim unbounded JSONL files.

Runs once per session start. Silent on success — never blocks startup.

Cleanup policy:
  tasks/*.json       → delete files older than ARTIFACT_TTL_DAYS (7)
  hooks-logs/*.jsonl → delete files older than LOG_TTL_DAYS (30)
  qg-history.jsonl   → keep last QG_HISTORY_MAX records (500)
  sprint-health.jsonl → keep last SPRINT_HEALTH_MAX records (100)

Exit codes: 0 (always — SessionStart cannot block)
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import log_event

_HOOK = "cleanup-artifacts"

DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)

ARTIFACT_TTL_DAYS = 7
LOG_TTL_DAYS = 30
QG_HISTORY_MAX = 500
SPRINT_HEALTH_MAX = 100


def delete_old_files(directory: Path, pattern: str, older_than_days: int) -> int:
    """Delete files matching pattern that are older than N days. Returns deleted count."""
    if not directory.exists():
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    deleted = 0
    for f in directory.glob(pattern):
        if f.is_file():
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
            if mtime < cutoff:
                try:
                    f.unlink()
                    deleted += 1
                except OSError:
                    pass
    return deleted


def trim_jsonl(filepath: Path, keep_last: int) -> int:
    """Keep only the last N lines in a JSONL file. Returns lines removed."""
    if not filepath.exists():
        return 0
    lines = filepath.read_text(encoding="utf-8").splitlines()
    # Filter out empty lines
    lines = [l for l in lines if l.strip()]
    if len(lines) <= keep_last:
        return 0
    removed = len(lines) - keep_last
    filepath.write_text("\n".join(lines[-keep_last:]) + "\n", encoding="utf-8")
    return removed


def main() -> None:
    stats: dict = {}

    try:
        n = delete_old_files(DATA_DIR / "tasks", "*.json", ARTIFACT_TTL_DAYS)
        if n:
            stats["artifacts_deleted"] = n
    except Exception as e:
        log_event(_HOOK, "WARN", {"step": "artifacts", "error": str(e)})

    try:
        n = delete_old_files(DATA_DIR / "hooks-logs", "*.jsonl", LOG_TTL_DAYS)
        if n:
            stats["logs_deleted"] = n
    except Exception as e:
        log_event(_HOOK, "WARN", {"step": "logs", "error": str(e)})

    try:
        n = trim_jsonl(DATA_DIR / "qg-history.jsonl", QG_HISTORY_MAX)
        if n:
            stats["qg_trimmed"] = n
    except Exception as e:
        log_event(_HOOK, "WARN", {"step": "qg-history", "error": str(e)})

    try:
        n = trim_jsonl(DATA_DIR / "sprint-health.jsonl", SPRINT_HEALTH_MAX)
        if n:
            stats["sprint_health_trimmed"] = n
    except Exception as e:
        log_event(_HOOK, "WARN", {"step": "sprint-health", "error": str(e)})

    if stats:
        log_event(_HOOK, "CLEANED", stats)

    print("{}")


if __name__ == "__main__":
    main()
