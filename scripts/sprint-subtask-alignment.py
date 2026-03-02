#!/usr/bin/env python3
"""Sprint subtask alignment checker and fixer.

Checks all subtasks in a sprint for:
1. HR8: Dates within parent range (start ≥ parent start, due ≤ parent due)
2. Missing dates (start_date, due_date)
3. Missing original_estimate (timetracking)

Fixes:
- Date violations → clamp to parent range
- Missing dates → distribute evenly within parent range
- Missing OE → estimate from summary keywords (conservative 4h default)

Usage:
    python3 scripts/sprint-subtask-alignment.py                    # dry-run current active sprint
    python3 scripts/sprint-subtask-alignment.py --sprint 640       # dry-run specific sprint
    python3 scripts/sprint-subtask-alignment.py --apply            # actually update Jira
    python3 scripts/sprint-subtask-alignment.py --report-only      # report without fix suggestions
"""

import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".claude", "skills", "atlassian-scripts"))

from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url

# --- Configuration ---
BOARD_ID = 2  # BEP board
SKIP_STATUSES = {"Done", "CANCELED"}
PARENT_TYPES = {"Story", "Task", "Bug"}

# Priority ordering (lower number = higher priority = gets earlier dates)
PRIORITY_ORDER = {"Highest": 1, "High": 2, "Medium": 3, "Low": 4, "Lowest": 5}

# Size → Hours mapping (for subtask OE estimation when parent has Size)
PARENT_SIZE_TO_SUBTASK_DEFAULT = {"XS": "2h", "S": "4h", "M": "4h", "L": "4h", "XL": "8h"}

# Keyword-based OE estimation for subtasks
OE_PATTERNS = [
    (r"migration|schema|table", "2h"),
    (r"enum|hook|toast|tab|routing|button|action|empty.?state|tag|filter", "2h"),
    (r"recheck|combine|review|audit", "2h"),
    (r"transformer|adapter|mapper", "2h"),
    (r"test|qa|spec", "4h"),
    (r"route.*controller|controller.*route|endpoint", "4h"),
    (r"usecase|repository|service", "4h"),
    (r"api.?integration|connect.*api|เชื่อมต่อ", "4h"),
    (r"component|layout|sidebar|drawer|panel|card|list|form", "4h"),
    (r"redlock|lock|race.?condition|security", "4h"),
    (r"loading|error.?state|success.?state|handle.*state", "2h"),
    (r"bug|fix|hotfix|แก้", "4h"),
]
DEFAULT_OE = "4h"


def estimate_oe(summary: str) -> str:
    """Estimate original_estimate from subtask summary keywords."""
    lower = summary.lower()
    for pattern, hours in OE_PATTERNS:
        if re.search(pattern, lower):
            return hours
    return DEFAULT_OE


def parse_date(val) -> str | None:
    """Extract date string from Jira field value."""
    if isinstance(val, dict):
        return val.get("value") or None
    return val or None


def clamp_date(date_str: str, min_date: str, max_date: str) -> str:
    """Clamp a date string within [min_date, max_date] range."""
    if date_str < min_date:
        return min_date
    if date_str > max_date:
        return max_date
    return date_str


def distribute_dates(count: int, parent_start: str, parent_due: str) -> list[tuple[str, str]]:
    """Distribute subtask dates evenly within parent range."""
    start = datetime.strptime(parent_start, "%Y-%m-%d")
    end = datetime.strptime(parent_due, "%Y-%m-%d")
    total_days = max((end - start).days, count)

    days_per = max(total_days // count, 1)
    results = []
    for i in range(count):
        s = start + timedelta(days=i * days_per)
        d = min(s + timedelta(days=days_per - 1), end)
        # Clamp to parent range
        s = max(s, start)
        d = min(d, end)
        results.append((s.strftime("%Y-%m-%d"), d.strftime("%Y-%m-%d")))
    return results


def main():
    dry_run = "--apply" not in sys.argv
    report_only = "--report-only" in sys.argv

    # Parse sprint ID
    sprint_id = None
    for i, arg in enumerate(sys.argv):
        if arg == "--sprint" and i + 1 < len(sys.argv):
            sprint_id = int(sys.argv[i + 1])

    if dry_run and not report_only:
        print("🔍 DRY RUN — use --apply to actually update Jira\n")
    elif report_only:
        print("📋 REPORT ONLY — no fixes suggested\n")
    else:
        print("⚡ APPLY MODE — updating Jira fields\n")

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

    # --- Phase 1: Fetch parent issues ---
    parent_fields = (
        "summary,status,issuetype,assignee,{{START_DATE_FIELD}},duedate,customfield_10016,customfield_10107,timetracking"
    )
    subtask_fields = "summary,status,issuetype,parent,assignee,priority,{{START_DATE_FIELD}},duedate,timetracking"
    result = api.get_sprint_issues(sprint_id, fields=parent_fields, max_results=50)
    all_issues = result.get("issues", [])

    parents = {}
    for issue in all_issues:
        key = issue["key"]
        f = issue.get("fields", {})
        status = f.get("status", {}).get("name", "?")
        itype = f.get("issuetype", {}).get("name", "?")

        if status in SKIP_STATUSES:
            continue
        if itype not in PARENT_TYPES:
            continue

        start = parse_date(f.get("{{START_DATE_FIELD}}"))
        due = f.get("duedate")
        size_obj = f.get("customfield_10107")
        size = size_obj.get("value") if isinstance(size_obj, dict) else size_obj
        assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")

        parents[key] = {
            "summary": f.get("summary", ""),
            "status": status,
            "type": itype,
            "start": start,
            "due": due,
            "size": size,
            "assignee": assignee,
        }

    print(f"Found {len(parents)} active parent issues\n")

    if not parents:
        print("No active parent issues found.")
        return 0

    # --- Phase 2: Fetch subtasks ---
    parent_keys = list(parents.keys())
    # JQL: fetch in batches of 20 (HR2: no ORDER BY with parent)
    all_subtasks = []
    for i in range(0, len(parent_keys), 20):
        batch = parent_keys[i : i + 20]
        jql = f"parent in ({','.join(batch)})"
        sub_result = api.search_issues(jql, fields=subtask_fields, max_results=50)
        all_subtasks.extend(sub_result.get("issues", []))

    # Filter out done
    active_subtasks = []
    for s in all_subtasks:
        f = s.get("fields", {})
        status = f.get("status", {}).get("name", "?")
        if status not in SKIP_STATUSES:
            active_subtasks.append(s)

    print(
        f"Found {len(all_subtasks)} subtasks ({len(active_subtasks)} active, {len(all_subtasks) - len(active_subtasks)} done)\n"
    )

    # --- Phase 3: Analyze alignment ---
    date_violations = []
    missing_dates = []
    missing_oe = []
    fixes = []  # (key, fields_to_update, reason)
    parent_extensions = {}  # parent_key → new_due (extend parent if subtasks overshoot)

    # Group subtasks by parent for date distribution
    # Sort each group by priority (Highest first → gets earlier dates)
    subtasks_by_parent: dict[str, list] = {}
    for s in active_subtasks:
        f = s.get("fields", {})
        parent_key = (f.get("parent") or {}).get("key")
        if parent_key and parent_key in parents:
            subtasks_by_parent.setdefault(parent_key, []).append(s)

    def subtask_priority_key(s):
        """Sort key: priority (Highest=1 first), then due date."""
        f = s.get("fields", {})
        p_name = (f.get("priority") or {}).get("name", "Medium")
        due = f.get("duedate") or "9999-12-31"
        return (PRIORITY_ORDER.get(p_name, 3), due)

    for parent_key in subtasks_by_parent:
        subtasks_by_parent[parent_key].sort(key=subtask_priority_key)

    # Pre-scan: find max subtask due per parent (to detect parent extension needed)
    for parent_key, subs in subtasks_by_parent.items():
        p = parents[parent_key]
        p_due = p["due"]
        if not p_due:
            continue
        max_sub_due = p_due
        for s in subs:
            sub_due = s.get("fields", {}).get("duedate")
            if sub_due and sub_due > max_sub_due:
                max_sub_due = sub_due
        if max_sub_due > p_due:
            parent_extensions[parent_key] = max_sub_due

    for s in active_subtasks:
        key = s["key"]
        f = s.get("fields", {})
        parent_key = (f.get("parent") or {}).get("key")

        if not parent_key or parent_key not in parents:
            continue

        p = parents[parent_key]
        p_start = p["start"]
        p_due = p["due"]

        if not p_start or not p_due:
            continue  # Parent has no dates — can't validate

        # Use extended parent due if applicable
        effective_p_due = parent_extensions.get(parent_key, p_due)

        sub_start = parse_date(f.get("{{START_DATE_FIELD}}"))
        sub_due = f.get("duedate")
        tt = f.get("timetracking", {}) or {}
        oe = tt.get("originalEstimate", "")

        update_fields: dict = {}

        # Check dates
        if not sub_start or not sub_due:
            missing_dates.append((key, parent_key, sub_start, sub_due))
            # Fix: distribute within parent range
            if not report_only:
                siblings = subtasks_by_parent.get(parent_key, [])
                missing_in_group = [
                    x
                    for x in siblings
                    if not parse_date(x.get("fields", {}).get("{{START_DATE_FIELD}}"))
                    or not x.get("fields", {}).get("duedate")
                ]
                if missing_in_group:
                    idx = next((i for i, x in enumerate(missing_in_group) if x["key"] == key), 0)
                    dates = distribute_dates(len(missing_in_group), p_start, effective_p_due)
                    if idx < len(dates):
                        new_start, new_due = dates[idx]
                        update_fields["{{START_DATE_FIELD}}"] = new_start
                        update_fields["duedate"] = new_due
        else:
            # Check HR8 violations — only flag start-before-parent (subtask too early)
            # For subtask-due > parent-due: extend parent instead of clamping subtask
            violations = []
            new_start = sub_start

            if sub_start < p_start:
                violations.append(f"start {sub_start} < parent start {p_start}")
                new_start = p_start
            if sub_due > p_due:
                violations.append(f"due {sub_due} > parent due {p_due} → extend parent to {effective_p_due}")

            if violations:
                date_violations.append((key, parent_key, sub_start, sub_due, p_start, p_due, "; ".join(violations)))
                if not report_only:
                    new_start = clamp_date(new_start, p_start, effective_p_due)
                    new_due = sub_due
                    # If due is before new start, move due to new start
                    if new_due < new_start:
                        new_due = new_start
                    if new_start != sub_start:
                        update_fields["{{START_DATE_FIELD}}"] = new_start
                    if new_due != sub_due:
                        update_fields["duedate"] = new_due

        # Check OE
        if not oe:
            missing_oe.append((key, parent_key, f.get("summary", "")))
            if not report_only:
                estimated = estimate_oe(f.get("summary", ""))
                update_fields["timetracking"] = {"originalEstimate": estimated}

        if update_fields:
            reason_parts = []
            if "{{START_DATE_FIELD}}" in update_fields or "duedate" in update_fields:
                reason_parts.append("dates")
            if "timetracking" in update_fields:
                reason_parts.append(f"OE={update_fields['timetracking']['originalEstimate']}")
            fixes.append((key, update_fields, ", ".join(reason_parts)))

    # Add parent extension fixes
    for parent_key, new_due in parent_extensions.items():
        p = parents[parent_key]
        if not report_only:
            fixes.append((parent_key, {"duedate": new_due}, f"extend due {p['due']}→{new_due} (subtasks overshoot)"))

    # --- Phase 4: Report ---
    print("=" * 70)
    print("SUBTASK ALIGNMENT REPORT")
    print("=" * 70)

    print(f"\n📅 DATE VIOLATIONS (HR8): {len(date_violations)}")
    for v in date_violations:
        print(f"  ❌ {v[0]} (parent {v[1]}): {v[2]}→{v[3]} vs parent {v[4]}→{v[5]}")
        print(f"     {v[6]}")

    print(f"\n📅 MISSING DATES: {len(missing_dates)}")
    for m in missing_dates:
        print(f"  ⚠️  {m[0]} (parent {m[1]}): start={m[2] or 'NONE'}, due={m[3] or 'NONE'}")

    print(f"\n⏱️  MISSING ORIGINAL ESTIMATE: {len(missing_oe)}/{len(active_subtasks)}")
    if missing_oe:
        for m in missing_oe[:10]:
            est = estimate_oe(m[2])
            print(f"  ⚠️  {m[0]} (parent {m[1]}): → {est} (estimated)")
        if len(missing_oe) > 10:
            print(f"  ... and {len(missing_oe) - 10} more")

    if report_only:
        print("\n📋 Report complete. Use without --report-only to see fix suggestions.")
        return 0

    # --- Phase 5: Apply fixes ---
    if not fixes:
        print("\n✅ No fixes needed — all subtasks aligned!")
        return 0

    print(f"\n{'=' * 70}")
    print(f"FIXES: {len(fixes)} subtasks to update")
    print(f"{'=' * 70}")

    updated = []
    errors = []

    # Print plan (always sequential — no I/O)
    for key, fields_to_update, reason in fixes:
        field_desc = ", ".join(f"{k}={v}" for k, v in fields_to_update.items())
        print(f"{'→' if dry_run else '⏳'} {key:<10} | {reason:<20} | {field_desc}")

    if not dry_run:
        # Apply all updates concurrently — each is an independent PATCH call
        from concurrent.futures import ThreadPoolExecutor

        def _apply(fix: tuple) -> tuple[str, str | None]:
            key, fields, _ = fix
            try:
                api.update_fields(key, fields)
                return key, None
            except Exception as exc:
                return key, str(exc)

        print()
        with ThreadPoolExecutor(max_workers=5) as pool:
            # map() preserves order; each result printed as it completes
            for key, err in pool.map(_apply, fixes):
                if err:
                    print(f"   ❌ {key}: {err}")
                    errors.append(f"{key}: {err}")
                else:
                    print(f"   ✅ {key}")
                    updated.append(key)
    else:
        updated = [key for key, _, _ in fixes]

    # Summary
    print(f"\n{'=' * 70}")
    print(f"Summary: {len(updated)} {'would update' if dry_run else 'updated'}, {len(errors)} errors")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  ❌ {e}")

    if not dry_run and updated:
        print(f"\n⚠️  Remember to cache_invalidate(sprint_id={sprint_id}) after this!")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
