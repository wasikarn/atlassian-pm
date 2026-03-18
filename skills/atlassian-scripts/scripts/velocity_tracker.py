#!/usr/bin/env python3
"""Track sprint velocity and update project-config.json automatically.

Fetches completed issues from a sprint, calculates story points and throughput,
then updates the velocity history in project-config.json.

Usage:
    # Track a completed sprint (by ID)
    python velocity_tracker.py --sprint-id 607

    # Track by sprint name
    python velocity_tracker.py --sprint-name "BEP Sprint-31"

    # Dry run (show data, don't update config)
    python velocity_tracker.py --sprint-id 607 --dry-run

    # Show current velocity summary
    python velocity_tracker.py --summary

Exit codes:
    0 = success
    1 = sprint not found or API error
    2 = credentials error
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import (
    APIError,
    CredentialsError,
    JiraAPI,
    create_ssl_context,
    derive_jira_url,
    get_auth_header,
    load_credentials,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "project-config.json"


def create_api() -> JiraAPI:
    """Create configured Jira API client."""
    creds = load_credentials()
    jira_url = derive_jira_url(creds["CONFLUENCE_URL"])
    return JiraAPI(
        base_url=jira_url,
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )


def load_config() -> dict:
    """Load project-config.json."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Save project-config.json with pretty formatting."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_sprint_info(api: JiraAPI, board_id: int, sprint_id: int) -> dict | None:
    """Get sprint details by ID."""
    try:
        result = api._request("GET", f"/rest/agile/1.0/sprint/{sprint_id}")
        return result
    except APIError:
        return None


def find_sprint_by_name(api: JiraAPI, board_id: int, name: str) -> dict | None:
    """Find sprint by name across all states."""
    for state in ["closed", "active", "future"]:
        try:
            result = api.get_board_sprints(board_id, state=state)
            for sprint in result.get("values", []):
                if sprint["name"] == name:
                    return sprint
        except APIError:
            continue
    return None


def get_completed_issues(api: JiraAPI, sprint_id: int) -> list[dict]:
    """Get all completed issues in a sprint with story points."""
    config = load_config()
    sp_field = config["jira"]["custom_fields"]["story_points"]

    all_issues = []
    start_at = 0

    while True:
        result = api.search_issues(
            jql=f"sprint = {sprint_id} AND status = Done",
            fields=f"summary,status,issuetype,assignee,{sp_field}",
            max_results=50,
            start_at=start_at,
        )

        issues = result.get("issues", [])
        all_issues.extend(issues)

        total = result.get("total", 0)
        if start_at + len(issues) >= total:
            break
        start_at += len(issues)

    return all_issues


def calculate_velocity(issues: list[dict], sp_field: str) -> dict:
    """Calculate velocity metrics from completed issues."""
    total_tickets = len(issues)
    total_sp = 0
    tickets_with_sp = 0
    per_assignee: dict[str, dict] = {}

    for issue in issues:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

        sp = fields.get(sp_field)
        if sp is not None:
            total_sp += sp
            tickets_with_sp += 1

        if assignee_name not in per_assignee:
            per_assignee[assignee_name] = {"tickets": 0, "sp": 0}
        per_assignee[assignee_name]["tickets"] += 1
        if sp is not None:
            per_assignee[assignee_name]["sp"] += sp

    return {
        "total_tickets": total_tickets,
        "total_sp": total_sp,
        "tickets_with_sp": tickets_with_sp,
        "sp_coverage": round(tickets_with_sp / total_tickets * 100, 1) if total_tickets > 0 else 0,
        "per_assignee": per_assignee,
    }


def update_config_velocity(config: dict, sprint: dict, velocity: dict) -> None:
    """Update velocity history in project-config.json."""
    team = config.setdefault("team", {})
    vel = team.setdefault("velocity", {})
    sp_data = vel.setdefault("story_points", {"avg_velocity": None, "sprints_tracked": 0, "history": []})
    throughput = vel.setdefault("throughput_history", [])

    sprint_name = sprint["name"]
    sprint_id = sprint["id"]
    dates = f"{sprint.get('startDate', '?')[:10]} - {sprint.get('endDate', '?')[:10]}"

    # Add to throughput history (avoid duplicates)
    existing_ids = {entry["id"] for entry in throughput}
    if sprint_id not in existing_ids:
        throughput.append(
            {
                "sprint": sprint_name,
                "id": sprint_id,
                "completed_tickets": velocity["total_tickets"],
                "completed_sp": velocity["total_sp"] if velocity["tickets_with_sp"] > 0 else None,
                "dates": dates,
            }
        )
        # Sort by sprint ID
        throughput.sort(key=lambda x: x["id"])

    # Update SP tracking if meaningful SP data exists (>50% coverage)
    if velocity["sp_coverage"] >= 50:
        sp_history = sp_data.setdefault("history", [])
        existing_sp_ids = {entry["id"] for entry in sp_history}
        if sprint_id not in existing_sp_ids:
            sp_history.append(
                {
                    "sprint": sprint_name,
                    "id": sprint_id,
                    "completed_sp": velocity["total_sp"],
                    "tickets_with_sp": velocity["tickets_with_sp"],
                    "total_tickets": velocity["total_tickets"],
                }
            )
            sp_history.sort(key=lambda x: x["id"])

        # Recalculate average velocity from last 5 sprints
        recent = sp_history[-5:]
        if recent:
            avg = sum(s["completed_sp"] for s in recent) / len(recent)
            sp_data["avg_velocity"] = round(avg, 1)
            sp_data["sprints_tracked"] = len(recent)

    # Update avg throughput
    recent_throughput = throughput[-5:]
    if recent_throughput:
        avg_tp = sum(t["completed_tickets"] for t in recent_throughput) / len(recent_throughput)
        vel["avg_throughput_per_sprint"] = round(avg_tp, 1)


def print_summary(config: dict) -> None:
    """Print current velocity summary."""
    vel = config.get("team", {}).get("velocity", {})

    print("=" * 60)
    print("Velocity Summary")
    print("=" * 60)

    # SP Velocity
    sp = vel.get("story_points", {})
    avg_vel = sp.get("avg_velocity")
    tracked = sp.get("sprints_tracked", 0)
    if avg_vel:
        print(f"\nStory Points Velocity: {avg_vel} SP/sprint (from {tracked} sprints)")
    else:
        print("\nStory Points Velocity: Not enough data (bootstrap phase)")
        print("  Need ≥50% SP coverage in sprints to start tracking")

    # Throughput
    print(f"\nAvg Throughput: {vel.get('avg_throughput_per_sprint', '?')} tickets/sprint")

    # History
    history = vel.get("throughput_history", [])
    if history:
        print("\nSprint History:")
        print(f"  {'Sprint':<20} {'Tickets':>8} {'SP':>6} {'Dates'}")
        print(f"  {'-' * 20} {'-' * 8} {'-' * 6} {'-' * 25}")
        for entry in history[-8:]:
            sp_str = str(entry.get("completed_sp", "-")) if entry.get("completed_sp") is not None else "-"
            print(f"  {entry['sprint']:<20} {entry['completed_tickets']:>8} {sp_str:>6} {entry.get('dates', '')}")

    # Team throughput
    members = config.get("team", {}).get("members", [])
    print("\nTeam Members:")
    print(f"  {'Name':<20} {'Role':<12} {'Focus':>6} {'Throughput':>12}")
    print(f"  {'-' * 20} {'-' * 12} {'-' * 6} {'-' * 12}")
    for m in members:
        ff = f"{m.get('focus_factor', '-')}" if m.get("focus_factor") else "-"
        tp = f"{m.get('avg_throughput', '-')} t/s" if m.get("avg_throughput") else "-"
        print(f"  {m['name']:<20} {m['role']:<12} {ff:>6} {tp:>12}")

    print("=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Track sprint velocity and update project-config.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sprint-id", type=int, help="Sprint ID to track")
    group.add_argument("--sprint-name", help="Sprint name to track (e.g., 'BEP Sprint-31')")
    group.add_argument("--summary", action="store_true", help="Show current velocity summary")
    parser.add_argument("--dry-run", action="store_true", help="Show data without updating config")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config()

    if args.summary:
        print_summary(config)
        return 0

    if not args.sprint_id and not args.sprint_name:
        parser.error("Specify --sprint-id, --sprint-name, or --summary")

    # Create API client
    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 2

    board_id = config["jira"]["board_id"]

    # Find sprint
    if args.sprint_id:
        sprint = get_sprint_info(api, board_id, args.sprint_id)
    else:
        sprint = find_sprint_by_name(api, board_id, args.sprint_name)

    if not sprint:
        logger.error("Sprint not found: %s", args.sprint_id or args.sprint_name)
        return 1

    sprint_name = sprint["name"]
    sprint_id = sprint["id"]
    print(f"Sprint: {sprint_name} (ID: {sprint_id})")
    print(f"State: {sprint.get('state', '?')}")
    print(f"Dates: {sprint.get('startDate', '?')[:10]} → {sprint.get('endDate', '?')[:10]}")

    # Get completed issues
    print("\nFetching completed issues...")
    issues = get_completed_issues(api, sprint_id)

    if not issues:
        print("No completed issues found.")
        return 0

    # Calculate velocity
    sp_field = config["jira"]["custom_fields"]["story_points"]
    velocity = calculate_velocity(issues, sp_field)

    # Display results
    print(f"\n{'=' * 60}")
    print(f"Velocity Report: {sprint_name}")
    print(f"{'=' * 60}")
    print(f"Completed tickets: {velocity['total_tickets']}")
    print(
        f"Story Points: {velocity['total_sp']} SP ({velocity['tickets_with_sp']}/{velocity['total_tickets']} tickets with SP = {velocity['sp_coverage']}%)"
    )

    if velocity["per_assignee"]:
        print("\nPer Assignee:")
        print(f"  {'Name':<25} {'Tickets':>8} {'SP':>6}")
        print(f"  {'-' * 25} {'-' * 8} {'-' * 6}")
        for name, data in sorted(velocity["per_assignee"].items(), key=lambda x: x[1]["tickets"], reverse=True):
            sp_str = str(data["sp"]) if data["sp"] > 0 else "-"
            print(f"  {name:<25} {data['tickets']:>8} {sp_str:>6}")

    if args.dry_run:
        print("\nDRY RUN — config not updated")
        return 0

    # Update config
    update_config_velocity(config, sprint, velocity)
    save_config(config)
    print(f"\nUpdated: {CONFIG_PATH}")
    print("HR6 Action: cache_invalidate may be needed if sprint items were modified")

    return 0


if __name__ == "__main__":
    sys.exit(main())
