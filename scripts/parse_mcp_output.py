#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""Parse large MCP tool outputs that exceed Claude's token limit.

Handles two MCP output formats:
  - MCP Atlassian: {"result": "{...JSON...}"}
  - Cache Server:  [{"type":"text","text":"{...JSON...}"}]

Usage:
  python3 scripts/parse-mcp-output.py <file>                   # default table
  python3 scripts/parse-mcp-output.py <file> --status "In Progress,TO FIX"
  python3 scripts/parse-mcp-output.py <file> --assignee {{SLOT_3}}
  python3 scripts/parse-mcp-output.py <file> --fields key,summary,status
  python3 scripts/parse-mcp-output.py <file> --json            # raw JSON output
  python3 scripts/parse-mcp-output.py <file> --csv             # CSV output

Examples (Claude Code context):
  # After MCP tool saves to file due to token limit:
  python3 scripts/parse-mcp-output.py /path/to/tool-output.txt
  python3 scripts/parse-mcp-output.py /path/to/tool-output.txt --status "To Do"
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys

# -- Field extractors ----------------------------------------------------------

FIELD_EXTRACTORS: dict[str, callable] = {
    "key": lambda i: i.get("key", ""),
    "id": lambda i: i.get("id", ""),
    "summary": lambda i: i.get("summary", "")[:60],
    "summary_full": lambda i: i.get("summary", ""),
    "status": lambda i: _nested(i, "status", "name"),
    "status_category": lambda i: _nested(i, "status", "category"),
    "priority": lambda i: _nested(i, "priority", "name"),
    "assignee": lambda i: _nested(i, "assignee", "display_name", fallback="Unassigned"),
    "parent": lambda i: _nested(i, "parent", "key"),
    "issuetype": lambda i: _nested(i, "issuetype", "name"),
    "labels": lambda i: (
        ",".join(i.get("labels", [])) if isinstance(i.get("labels"), list) else str(i.get("labels", ""))
    ),
    "start_date": lambda i: _custom_field_value(i, "{{START_DATE_FIELD}}"),
    "sprint": lambda i: _custom_field_value(i, "{{SPRINT_FIELD}}"),
    "duedate": lambda i: i.get("duedate", ""),
    "created": lambda i: i.get("created", "")[:10],
    "updated": lambda i: i.get("updated", "")[:10],
}

DEFAULT_FIELDS = ["key", "status", "start_date", "assignee", "summary"]


def _nested(issue: dict, *keys: str, fallback: str = "") -> str:
    """Extract nested dict value: issue[key1][key2]..."""
    val = issue
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, {})
        else:
            return fallback
    return str(val) if val and val != {} else fallback


def _custom_field_value(issue: dict, field: str) -> str:
    """Extract custom field — handles both {value: X} and plain X."""
    raw = issue.get(field)
    if raw is None:
        return ""
    if isinstance(raw, dict):
        return str(raw.get("value", "")) if raw.get("value") is not None else ""
    return str(raw)


# -- JSON parsing --------------------------------------------------------------


def parse_mcp_output(file_path: str) -> list[dict]:
    """Parse MCP tool output file → list of issue dicts.

    Auto-detects format:
      1. {"result": "{...}"} — MCP Atlassian (jira_search, jira_get_sprint_issues)
      2. [{"type":"text","text":"{...}"}] — Cache server (cache_search, cache_sprint_issues)
      3. Plain JSON with issues array
    """
    with open(file_path, encoding="utf-8") as f:
        raw = json.load(f)

    # Format 1: MCP Atlassian — {"result": "JSON_STRING"}
    if isinstance(raw, dict) and "result" in raw:
        inner = raw["result"]
        if isinstance(inner, str):
            data = json.loads(inner)
        else:
            data = inner
        return _extract_issues(data)

    # Format 2: Cache server — [{"type":"text", "text":"JSON_STRING"}]
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
        text = raw[0]["text"]
        if isinstance(text, str):
            data = json.loads(text)
        else:
            data = text
        # Cache server wraps in {results: {issues: [...]}}
        if isinstance(data, dict) and "results" in data:
            return _extract_issues(data["results"])
        return _extract_issues(data)

    # Format 3: Plain JSON
    if isinstance(raw, dict):
        return _extract_issues(raw)
    if isinstance(raw, list):
        return raw  # assume list of issues

    return []


def _extract_issues(data: dict) -> list[dict]:
    """Extract issues array from parsed data, normalizing nested fields."""
    issues = []
    if isinstance(data, dict):
        # Try common keys
        for key in ("issues", "results", "data"):
            if key in data and isinstance(data[key], list):
                issues = data[key]
                break
        # Maybe it has subtasks
        if not issues and "subtasks" in data and isinstance(data["subtasks"], list):
            issues = data["subtasks"]

    # Normalize: if issues have `fields` key, flatten it
    # Raw Jira API: {key, fields: {summary, status, ...}}
    # MCP Atlassian: {key, summary, status, ...} (already flat)
    if issues and isinstance(issues[0], dict) and "fields" in issues[0]:
        normalized = []
        for issue in issues:
            flat = {k: v for k, v in issue.items() if k != "fields"}
            if isinstance(issue.get("fields"), dict):
                flat.update(issue["fields"])
            normalized.append(flat)
        return normalized

    return issues


# -- Filtering -----------------------------------------------------------------


def filter_issues(
    issues: list[dict],
    status: str | None = None,
    assignee: str | None = None,
    issuetype: str | None = None,
) -> list[dict]:
    """Filter issues by criteria. Comma-separated values = OR match."""
    result = issues

    if status:
        allowed = {s.strip().lower() for s in status.split(",")}
        result = [i for i in result if _nested(i, "status", "name").lower() in allowed]

    if assignee:
        term = assignee.lower()
        result = [
            i
            for i in result
            if term in _nested(i, "assignee", "display_name", fallback="").lower()
            or term in _nested(i, "assignee", "name", fallback="").lower()
        ]

    if issuetype:
        allowed = {t.strip().lower() for t in issuetype.split(",")}
        result = [i for i in result if _nested(i, "issuetype", "name").lower() in allowed]

    return result


# -- Output formatters ---------------------------------------------------------


def format_table(issues: list[dict], fields: list[str]) -> str:
    """Format issues as aligned text table."""
    if not issues:
        return "(no issues found)"

    # Build rows
    headers = fields
    rows = []
    for issue in issues:
        row = []
        for f in fields:
            extractor = FIELD_EXTRACTORS.get(f, lambda i, f=f: str(i.get(f, "")))
            row.append(extractor(issue))
        rows.append(row)

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    # Cap widths to avoid overflow
    max_width = {"summary": 55, "summary_full": 80, "labels": 30}
    for i, f in enumerate(fields):
        if f in max_width:
            widths[i] = min(widths[i], max_width[f])

    # Format
    lines = []
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))

    for row in rows:
        line = "  ".join(val[: widths[i]].ljust(widths[i]) for i, val in enumerate(row))
        lines.append(line)

    return "\n".join(lines)


def format_json(issues: list[dict], fields: list[str]) -> str:
    """Format as filtered JSON."""
    filtered = []
    for issue in issues:
        obj = {}
        for f in fields:
            extractor = FIELD_EXTRACTORS.get(f, lambda i, f=f: str(i.get(f, "")))
            obj[f] = extractor(issue)
        filtered.append(obj)
    return json.dumps(filtered, ensure_ascii=False, indent=2)


def format_csv_output(issues: list[dict], fields: list[str]) -> str:
    """Format as CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(fields)
    for issue in issues:
        row = []
        for f in fields:
            extractor = FIELD_EXTRACTORS.get(f, lambda i, f=f: str(i.get(f, "")))
            row.append(extractor(issue))
        writer.writerow(row)
    return buf.getvalue()


# -- Main ----------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Parse large MCP tool outputs into readable tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file", help="Path to MCP tool output file")
    parser.add_argument(
        "--fields",
        "-f",
        default=",".join(DEFAULT_FIELDS),
        help=f"Comma-separated fields (default: {','.join(DEFAULT_FIELDS)}). "
        f"Available: {','.join(sorted(FIELD_EXTRACTORS.keys()))}",
    )
    parser.add_argument("--status", "-s", help="Filter by status (comma-separated)")
    parser.add_argument("--assignee", "-a", help="Filter by assignee (substring match)")
    parser.add_argument("--issuetype", "-t", help="Filter by issue type (comma-separated)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--csv", action="store_true", help="Output as CSV")
    parser.add_argument("--count", "-c", action="store_true", help="Show count only")

    args = parser.parse_args()

    # Parse
    try:
        issues = parse_mcp_output(args.file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter
    issues = filter_issues(
        issues,
        status=args.status,
        assignee=args.assignee,
        issuetype=args.issuetype,
    )

    # Count
    print(f"# {len(issues)} issues", file=sys.stderr)

    if args.count:
        sys.exit(0)

    # Format
    fields = [f.strip() for f in args.fields.split(",")]

    if args.json:
        print(format_json(issues, fields))
    elif args.csv:
        print(format_csv_output(issues, fields))
    else:
        print(format_table(issues, fields))


if __name__ == "__main__":
    main()
