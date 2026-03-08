#!/usr/bin/env python3
"""Re-rank sprint issues on Jira Board by due date + priority.

Sorts all parent issues (Story/Task/Bug) in a sprint by:
1. Due date (ascending — earliest first)
2. Priority (Highest → Lowest)

This changes the actual board/backlog ordering in Jira.

Usage:
    python3 scripts/sprint-rank-by-date.py                    # dry-run active sprint
    python3 scripts/sprint-rank-by-date.py --sprint 640       # dry-run specific sprint
    python3 scripts/sprint-rank-by-date.py --apply            # actually re-rank in Jira
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".claude", "skills", "atlassian-scripts"))

from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

# --- Configuration ---
BOARD_ID = 2  # BEP board
SKIP_STATUSES = {"Done", "CANCELED"}
PARENT_TYPES = {"Story", "Task", "Bug"}

# Priority ordering (lower number = higher priority = ranked first)
PRIORITY_ORDER = {"Highest": 1, "High": 2, "Medium": 3, "Low": 4, "Lowest": 5}


def main():
    dry_run = "--apply" not in sys.argv

    # Parse sprint ID
    sprint_id = None
    for i, arg in enumerate(sys.argv):
        if arg == "--sprint" and i + 1 < len(sys.argv):
            sprint_id = int(sys.argv[i + 1])

    if dry_run:
        print("🔍 DRY RUN — use --apply to actually re-rank in Jira\n")
    else:
        print("⚡ APPLY MODE — re-ranking issues in Jira\n")

    # Connect
    creds = load_credentials()
    api = JiraAPI(
        base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    # Auto-detect sprint if not specified
    if not sprint_id:
        sprints = api.get_board_sprints(BOARD_ID, state="active")
        active = sprints.get("values", [])
        if active:
            sprint_id = active[0]["id"]
            sprint_name = active[0]["name"]
            print(f"Auto-detected active sprint: {sprint_name} (ID: {sprint_id})")
        else:
            print("❌ No active sprint found. Use --sprint <id>")
            return 1

    # Fetch sprint issues
    fields = "summary,status,issuetype,priority,duedate,assignee"
    result = api.get_sprint_issues(sprint_id, fields=fields, max_results=50)
    all_issues = result.get("issues", [])

    # Filter to active parent issues only
    parents = []
    for issue in all_issues:
        f = issue.get("fields", {})
        status = f.get("status", {}).get("name", "?")
        itype = f.get("issuetype", {}).get("name", "?")

        if status in SKIP_STATUSES:
            continue
        if itype not in PARENT_TYPES:
            continue

        due = f.get("duedate") or "9999-12-31"
        priority_name = (f.get("priority") or {}).get("name", "Medium")
        priority_rank = PRIORITY_ORDER.get(priority_name, 3)
        assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")

        parents.append(
            {
                "key": issue["key"],
                "summary": f.get("summary", ""),
                "status": status,
                "type": itype,
                "due": due,
                "priority": priority_name,
                "priority_rank": priority_rank,
                "assignee": assignee,
            }
        )

    print(f"\nFound {len(parents)} active parent issues\n")

    if len(parents) < 2:
        print("Not enough issues to re-rank.")
        return 0

    # Sort by due date ASC, then priority rank ASC (Highest=1 first)
    sorted_parents = sorted(parents, key=lambda x: (x["due"], x["priority_rank"]))

    # Display sorted order
    print(f"{'#':<3} {'Key':<12} {'Due':<12} {'Priority':<10} {'Status':<16} {'Summary'}")
    print("-" * 100)
    for i, p in enumerate(sorted_parents, 1):
        due_display = p["due"] if p["due"] != "9999-12-31" else "NO DATE"
        print(f"{i:<3} {p['key']:<12} {due_display:<12} {p['priority']:<10} {p['status']:<16} {p['summary'][:50]}")

    if dry_run:
        print(f"\n📋 Would re-rank {len(sorted_parents)} issues in this order.")
        print("Use --apply to execute.")
        return 0

    # Apply ranking: rank each issue after the previous one
    print(f"\n⚡ Re-ranking {len(sorted_parents)} issues...")
    errors = []

    for i in range(1, len(sorted_parents)):
        current_key = sorted_parents[i]["key"]
        prev_key = sorted_parents[i - 1]["key"]

        try:
            api.rank_issues([current_key], rank_after_key=prev_key)
            print(f"  ✅ {current_key} ranked after {prev_key}")
        except Exception as e:
            print(f"  ❌ {current_key}: {e}")
            errors.append(f"{current_key}: {e}")

    # Summary
    ranked = len(sorted_parents) - 1 - len(errors)
    print(f"\n{'=' * 60}")
    print(f"Summary: {ranked} ranked, {len(errors)} errors")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  ❌ {e}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
