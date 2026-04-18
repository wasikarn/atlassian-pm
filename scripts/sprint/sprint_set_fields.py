#!/usr/bin/env python3
"""Batch set estimation fields for sprint issues based on Size field.

Sets Story Points on stories/tasks and timetracking (Original Estimate)
on subtasks, derived from the Size (T-shirt) field.

Size → SP: XS=1, S=2, M=3, L=5, XL=8
Size → Hours: XS=2h, S=4h, M=8h, L=16h, XL=32h

Usage:
    python3 scripts/sprint-set-fields.py --sprint 673
    python3 scripts/sprint-set-fields.py --sprint 673 --apply
    python3 scripts/sprint-set-fields.py --sprint 673 --force
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

# --- Mappings ---
SIZE_TO_SP = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}
SIZE_TO_HOURS = {"XS": "2h", "S": "4h", "M": "8h", "L": "16h", "XL": "32h"}

SKIP_STATUSES = {"Done", "CANCELED"}

FIELDS = "summary,status,issuetype,parent,customfield_10016,customfield_10107,timetracking"


def extract_size_letter(size_value: str | None) -> str | None:
    """Extract size letter from Jira value like 'M (1-2 days)'."""
    if not size_value:
        return None
    token = size_value.strip().split()[0].upper()
    return token if token in SIZE_TO_SP else None


def fetch_all_sprint_issues(api: JiraAPI, sprint_id: int) -> list[dict]:
    """Fetch all issues in a sprint with pagination."""
    issues = []
    start_at = 0
    while True:
        result = api.get_sprint_issues(sprint_id, fields=FIELDS, max_results=50, start_at=start_at)
        batch = result.get("issues", [])
        if not batch:
            break
        issues.extend(batch)
        if len(batch) < 50:
            break
        start_at += len(batch)
    return issues


def main():
    parser = argparse.ArgumentParser(description="Set estimation fields from Size for sprint issues")
    parser.add_argument("--sprint", required=True, type=int, help="Sprint ID (e.g., 673)")
    parser.add_argument("--apply", action="store_true", help="Actually update Jira (default: dry-run)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing SP/OE values")
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        print(f"DRY RUN — sprint {args.sprint} — use --apply to update Jira\n")
    else:
        print(f"APPLY MODE — sprint {args.sprint} — updating Jira fields\n")

    # Connect
    creds = load_credentials()
    api = JiraAPI(
        base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    # Fetch
    issues = fetch_all_sprint_issues(api, args.sprint)
    print(f"Found {len(issues)} issues in sprint {args.sprint}\n")

    skipped = []
    errors = []

    # Phase A: Analysis — compute updates (no I/O, fast)
    work_items: list[tuple[str, dict, str, str, str, str | None]] = []
    # Each item: (key, update_fields, field_desc, summary, issue_type, size_letter)

    for issue in issues:
        key = issue.get("key", "?")
        f = issue.get("fields", {})
        status = f.get("status", {}).get("name", "?")
        issue_type = f.get("issuetype", {}).get("name", "?")
        summary = f.get("summary", "")[:60]
        parent = f.get("parent", {})
        is_subtask = bool(parent and parent.get("key"))

        if status in SKIP_STATUSES:
            skipped.append(f"{key} ({status})")
            continue

        # Current values
        sp = f.get("customfield_10016")
        size_obj = f.get("customfield_10107")
        size_value = size_obj.get("value") if isinstance(size_obj, dict) else size_obj
        size_letter = extract_size_letter(size_value)

        tt = f.get("timetracking", {}) or {}
        original_est = tt.get("originalEstimate")

        # Subtask-level: has parent and not Story/Bug
        is_subtask_level = is_subtask and issue_type not in ("Story", "Bug")

        update_fields = {}

        if is_subtask_level:
            if size_letter and (not original_est or args.force):
                hours = SIZE_TO_HOURS.get(size_letter)
                if hours:
                    update_fields["timetracking"] = {"originalEstimate": hours}
        else:
            if size_letter and (not sp or args.force):
                update_fields["customfield_10016"] = SIZE_TO_SP[size_letter]

        if not update_fields:
            skipped.append(f"{key} (no update needed)")
            continue

        field_desc = ", ".join(f"{k}={v}" for k, v in update_fields.items())
        work_items.append((key, update_fields, field_desc, summary, issue_type, size_letter))

    # Phase B: Print plan (always sequential — no I/O)
    for key, _, field_desc, summary, issue_type, size_letter in work_items:
        marker = "  ->" if dry_run else "  ⏳"
        print(f"{marker} {key:<10} {issue_type:<10} Size={size_letter or '-':<3} | {field_desc}")
        print(f"     {summary}")

    # Phase C: Apply concurrently (or dry-run skip)
    updated = []
    if not dry_run and work_items:
        from concurrent.futures import ThreadPoolExecutor

        def _apply(item: tuple) -> tuple[str, str | None]:
            key, uf = item[0], item[1]
            try:
                api.update_fields(key, uf)
                return key, None
            except Exception as exc:
                return key, str(exc)

        print()
        with ThreadPoolExecutor(max_workers=5) as pool:
            for key, err in pool.map(_apply, work_items):
                if err:
                    print(f"     ❌ {key}: {err}")
                    errors.append(f"{key}: {err}")
                else:
                    print(f"     ✅ {key}")
                    updated.append(key)
    elif dry_run:
        updated = [item[0] for item in work_items]

    # Summary
    print(f"\n{'=' * 60}")
    verb = "would update" if dry_run else "updated"
    print(f"Summary: {len(updated)} {verb}, {len(skipped)} skipped, {len(errors)} errors")

    if skipped:
        print(f"\nSkipped: {', '.join(skipped[:10])}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}")

    if not dry_run and updated:
        print("\nRemember: cache_invalidate after this!")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
