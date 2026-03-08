#!/usr/bin/env python3
"""Batch clear start date and due date from sprint tickets.

Usage:
    python3 scripts/clear-sprint-dates.py --sprint 673
    python3 scripts/clear-sprint-dates.py --sprint 673 --dry-run
    python3 scripts/clear-sprint-dates.py --sprint 673 --fields duedate
    python3 scripts/clear-sprint-dates.py --sprint 673 --fields customfield_10015,duedate
    python3 scripts/clear-sprint-dates.py --sprint 673 --jql "status != Done"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts"))

from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

DEFAULT_FIELDS = ["customfield_10015", "duedate"]
FIELD_LABELS = {
    "customfield_10015": "Start Date",
    "duedate": "Due Date",
}


def fetch_all_tickets(api: JiraAPI, jql: str, fields: list[str]) -> list[dict]:
    """Fetch all tickets matching JQL with pagination."""
    tickets = []
    start_at = 0
    while True:
        result = api.search_issues(jql, fields=",".join(["key", *fields]), max_results=50, start_at=start_at)
        issues = result.get("issues", [])
        if not issues:
            break
        tickets.extend(issues)
        # stop if we got fewer than max
        if len(issues) < 50:
            break
        start_at += len(issues)
    return tickets


def has_dates(issue: dict, fields: list[str]) -> bool:
    """Check if issue has any non-null date fields."""
    f = issue.get("fields", {})
    return any(f.get(field) is not None for field in fields)


def main():
    parser = argparse.ArgumentParser(description="Clear date fields from sprint tickets")
    parser.add_argument("--sprint", required=True, type=int, help="Sprint ID (e.g., 673)")
    parser.add_argument("--project", default="BEP", help="Project key (default: BEP)")
    parser.add_argument(
        "--fields",
        default=",".join(DEFAULT_FIELDS),
        help=f"Comma-separated field IDs to clear (default: {','.join(DEFAULT_FIELDS)})",
    )
    parser.add_argument("--jql", default="", help="Additional JQL filter (e.g., 'status != Done')")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleared without making changes")
    args = parser.parse_args()

    fields = [f.strip() for f in args.fields.split(",")]
    field_names = " + ".join(FIELD_LABELS.get(f, f) for f in fields)

    # Build JQL
    jql = f"sprint = {args.sprint} AND project = {args.project}"
    if args.jql:
        jql += f" AND ({args.jql})"

    # Connect
    creds = load_credentials()
    api = JiraAPI(
        base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    # Fetch
    print(f"Fetching tickets: {jql}")
    all_tickets = fetch_all_tickets(api, jql, fields)
    tickets_with_dates = [t for t in all_tickets if has_dates(t, fields)]

    print(f"Found {len(all_tickets)} tickets, {len(tickets_with_dates)} have dates to clear ({field_names})")
    if not tickets_with_dates:
        print("Nothing to do.")
        return

    if args.dry_run:
        print("\n[DRY RUN] Would clear:")
        for t in tickets_with_dates:
            f = t.get("fields", {})
            vals = ", ".join(f"{FIELD_LABELS.get(k, k)}={f.get(k)}" for k in fields if f.get(k) is not None)
            print(f"  {t['key']} — {vals}")
        return

    # Clear
    success = 0
    failed = []
    null_fields = {f: None for f in fields}

    for t in tickets_with_dates:
        key = t["key"]
        try:
            status = api.update_fields(key, null_fields)
            if status == 204:
                print(f"  ✓ {key}")
                success += 1
            else:
                print(f"  ⚠ {key} — HTTP {status}")
                failed.append(key)
        except Exception as e:
            print(f"  ✗ {key} — {e}")
            failed.append(key)

    print(f"\nDone: {success}/{len(tickets_with_dates)} cleared")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
