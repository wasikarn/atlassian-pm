#!/usr/bin/env python3
"""Generate activity report from claude-mem database.

Usage:
    python generate_report.py                          # Today
    python generate_report.py --hours 48               # Last 48 hours
    python generate_report.py --start 2026-02-05       # Date range
    python generate_report.py --start 2026-02-05 --end 2026-02-06
    python generate_report.py --project jira-generator  # Filter project
    python generate_report.py --types bugfix,decision   # Filter types
    python generate_report.py --format json             # JSON output
    python generate_report.py --output report.md        # Save to file
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path.home() / ".claude-mem" / "claude-mem.db"

VALID_TYPES = {"decision", "bugfix", "feature", "refactor", "discovery", "change"}

TYPE_ICONS = {
    "decision": "\u2696\ufe0f",
    "bugfix": "\U0001f534",
    "feature": "\U0001f7e3",
    "refactor": "\U0001f504",
    "discovery": "\U0001f535",
    "change": "\u2705",
}

# Bangkok timezone (UTC+7)
TZ_OFFSET = timezone(timedelta(hours=7))


class ClaudeMemDB:
    """Read-only SQLite client for claude-mem database."""

    def __init__(self, db_path: Path):
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        uri = f"file:{db_path}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def get_sessions(self, start_epoch: int, end_epoch: int, project: str | None = None) -> list[dict]:
        sql = """
            SELECT
                memory_session_id, project, user_prompt,
                started_at, started_at_epoch,
                completed_at, completed_at_epoch,
                status, prompt_counter
            FROM sdk_sessions
            WHERE started_at_epoch >= ? AND started_at_epoch <= ?
        """
        params: list = [start_epoch, end_epoch]
        if project:
            sql += " AND project LIKE ?"
            params.append(f"%{project}%")
        sql += " ORDER BY started_at_epoch ASC"
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_observations(
        self,
        start_epoch: int,
        end_epoch: int,
        project: str | None = None,
        types: list[str] | None = None,
    ) -> list[dict]:
        sql = """
            SELECT
                o.id, o.memory_session_id, o.project, o.type,
                o.title, o.subtitle, o.facts, o.files_read,
                o.files_modified, o.created_at, o.created_at_epoch,
                o.discovery_tokens
            FROM observations o
            WHERE o.created_at_epoch >= ? AND o.created_at_epoch <= ?
        """
        params: list = [start_epoch, end_epoch]
        if project:
            sql += " AND o.project LIKE ?"
            params.append(f"%{project}%")
        if types:
            placeholders = ",".join("?" for _ in types)
            sql += f" AND o.type IN ({placeholders})"
            params.extend(types)
        sql += " ORDER BY o.created_at_epoch ASC"
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self, start_epoch: int, end_epoch: int, project: str | None = None) -> dict:
        sql = """
            SELECT
                COUNT(DISTINCT memory_session_id) as session_count,
                COUNT(*) as observation_count,
                COALESCE(SUM(CASE WHEN type = 'decision' THEN 1 ELSE 0 END), 0) as decisions,
                COALESCE(SUM(CASE WHEN type = 'bugfix' THEN 1 ELSE 0 END), 0) as bugfixes,
                COALESCE(SUM(CASE WHEN type = 'feature' THEN 1 ELSE 0 END), 0) as features,
                COALESCE(SUM(CASE WHEN type = 'refactor' THEN 1 ELSE 0 END), 0) as refactors,
                COALESCE(SUM(CASE WHEN type = 'discovery' THEN 1 ELSE 0 END), 0) as discoveries,
                COALESCE(SUM(CASE WHEN type = 'change' THEN 1 ELSE 0 END), 0) as changes,
                COALESCE(SUM(discovery_tokens), 0) as total_tokens
            FROM observations
            WHERE created_at_epoch >= ? AND created_at_epoch <= ?
        """
        params: list = [start_epoch, end_epoch]
        if project:
            sql += " AND project LIKE ?"
            params.append(f"%{project}%")
        row = self.conn.execute(sql, params).fetchone()
        return dict(row)


def parse_json_field(value: str | None) -> list:
    """Safely parse a JSON field that might be null or malformed."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def format_tokens(tokens: int) -> str:
    """Format token count as human-readable string."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.0f}K"
    return str(tokens)


def epoch_to_local(epoch: int) -> datetime:
    """Convert epoch (milliseconds) to local datetime (Bangkok UTC+7)."""
    return datetime.fromtimestamp(epoch / 1000, tz=TZ_OFFSET)


def format_time(epoch: int) -> str:
    """Format epoch as HH:MM AM/PM."""
    return epoch_to_local(epoch).strftime("%-I:%M %p")


def format_date(epoch: int) -> str:
    """Format epoch as readable date."""
    return epoch_to_local(epoch).strftime("%b %-d, %Y")


# --- Markdown Formatter ---


def generate_markdown(
    sessions: list[dict],
    observations: list[dict],
    stats: dict,
    project_filter: str | None,
    start_dt: datetime,
    end_dt: datetime,
) -> str:
    lines: list[str] = []
    date_range = _date_range_str(start_dt, end_dt)
    project_label = project_filter or "all projects"

    # Header
    lines.append(f"# Activity Report: {date_range}")
    lines.append(
        f"**Project:** {project_label} | "
        f"**Sessions:** {stats['session_count']} | "
        f"**Observations:** {stats['observation_count']} | "
        f"**Tokens:** {format_tokens(stats['total_tokens'])}"
    )
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Type | Count |")
    lines.append("|------|-------|")
    type_map = [
        ("change", stats["changes"]),
        ("discovery", stats["discoveries"]),
        ("feature", stats["features"]),
        ("decision", stats["decisions"]),
        ("bugfix", stats["bugfixes"]),
        ("refactor", stats["refactors"]),
    ]
    for tname, count in type_map:
        if count > 0:
            icon = TYPE_ICONS.get(tname, "")
            lines.append(f"| {icon} {tname} | {count} |")
    lines.append("")

    # Group observations by date
    obs_by_date: dict[str, list[dict]] = {}
    for obs in observations:
        date_key = format_date(obs["created_at_epoch"])
        obs_by_date.setdefault(date_key, []).append(obs)

    # Build session lookup: memory_session_id -> session info
    session_map: dict[str, dict] = {}
    for s in sessions:
        session_map[s["memory_session_id"]] = s

    # Sessions by date
    for date_key, day_obs in obs_by_date.items():
        lines.append(f"## {date_key}")
        lines.append("")

        # Group by session
        obs_by_session: dict[str, list[dict]] = {}
        for obs in day_obs:
            sid = obs["memory_session_id"] or "unknown"
            obs_by_session.setdefault(sid, []).append(obs)

        for sid, s_obs in obs_by_session.items():
            session = session_map.get(sid)
            time_str = format_time(s_obs[0]["created_at_epoch"])
            prompt = _truncate(session["user_prompt"], 80) if session else "—"
            prompts = session["prompt_counter"] if session else "?"

            lines.append(f"### {time_str} — {prompt}")
            lines.append(f"**Prompts:** {prompts} | **Observations:** {len(s_obs)}")
            lines.append("")

            for obs in s_obs:
                icon = TYPE_ICONS.get(obs["type"], "")
                lines.append(f"- {icon} [{obs['type']}] {obs['title']}")
            lines.append("")

    # Files modified (top 10)
    file_counts = Counter()
    for obs in observations:
        for f in parse_json_field(obs.get("files_modified")):
            file_counts[f] += 1

    if file_counts:
        lines.append("## Files Modified (top 10)")
        lines.append("")
        lines.append("| File | Changes |")
        lines.append("|------|---------|")
        for filepath, count in file_counts.most_common(10):
            short = _shorten_path(filepath)
            lines.append(f"| `{short}` | {count} |")
        lines.append("")

    return "\n".join(lines)


def _date_range_str(start: datetime, end: datetime) -> str:
    s = start.strftime("%b %-d, %Y")
    e = end.strftime("%b %-d, %Y")
    if s == e:
        return s
    return f"{s} — {e}"


def _truncate(text: str | None, max_len: int) -> str:
    if not text:
        return "—"
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _shorten_path(filepath: str) -> str:
    """Shorten absolute path for display."""
    home = str(Path.home())
    if filepath.startswith(home):
        return "~" + filepath[len(home) :]
    return filepath


# --- JSON Formatter ---


def generate_json_output(
    sessions: list[dict],
    observations: list[dict],
    stats: dict,
    project_filter: str | None,
    start_dt: datetime,
    end_dt: datetime,
) -> str:
    report = {
        "metadata": {
            "generated_at": datetime.now(tz=TZ_OFFSET).isoformat(),
            "date_range": {
                "start": start_dt.strftime("%Y-%m-%d"),
                "end": end_dt.strftime("%Y-%m-%d"),
            },
            "project": project_filter,
        },
        "statistics": stats,
        "sessions": [
            {
                "id": s["memory_session_id"],
                "prompt": _truncate(s["user_prompt"], 200),
                "started_at": s["started_at"],
                "status": s["status"],
                "prompts": s["prompt_counter"],
            }
            for s in sessions
        ],
        "observations": [
            {
                "id": o["id"],
                "type": o["type"],
                "title": o["title"],
                "created_at": o["created_at"],
                "tokens": o["discovery_tokens"],
                "files_modified": parse_json_field(o.get("files_modified")),
            }
            for o in observations
        ],
    }
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)


# --- CLI ---


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate activity report from claude-mem database")
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Report for last N hours (default: today)",
    )
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--project", type=str, help="Filter by project name (substring match)")
    parser.add_argument(
        "--types",
        type=str,
        help=f"Comma-separated observation types: {','.join(sorted(VALID_TYPES))}",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument("--output", type=str, help="Save to file instead of stdout")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Database path")
    return parser.parse_args()


def resolve_time_range(args: argparse.Namespace) -> tuple[datetime, datetime]:
    """Resolve start/end datetimes from CLI arguments."""
    now = datetime.now(tz=TZ_OFFSET)

    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=TZ_OFFSET)
    elif args.hours:
        start = now - timedelta(hours=args.hours)
    else:
        # Default: today from midnight
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if args.end:
        end = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=TZ_OFFSET)
        # End of day
        end = end.replace(hour=23, minute=59, second=59)
    else:
        end = now

    return start, end


def main():
    args = parse_args()

    # Resolve time range
    start_dt, end_dt = resolve_time_range(args)
    # claude-mem stores epochs in milliseconds
    start_epoch = int(start_dt.timestamp() * 1000)
    end_epoch = int(end_dt.timestamp() * 1000)

    # Parse type filter
    types = None
    if args.types:
        types = [t.strip() for t in args.types.split(",")]
        invalid = set(types) - VALID_TYPES
        if invalid:
            print(f"Error: Invalid types: {invalid}", file=sys.stderr)
            print(f"Valid types: {sorted(VALID_TYPES)}", file=sys.stderr)
            sys.exit(1)

    # Connect to database
    db_path = Path(args.db)
    try:
        db = ClaudeMemDB(db_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Query data
        sessions = db.get_sessions(start_epoch, end_epoch, args.project)
        observations = db.get_observations(start_epoch, end_epoch, args.project, types)
        stats = db.get_stats(start_epoch, end_epoch, args.project)

        # Format output
        if args.format == "json":
            output = generate_json_output(sessions, observations, stats, args.project, start_dt, end_dt)
        else:
            output = generate_markdown(sessions, observations, stats, args.project, start_dt, end_dt)

        # Write output
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Report saved to: {args.output}", file=sys.stderr)
        else:
            print(output)

    finally:
        db.close()


if __name__ == "__main__":
    main()
