#!/usr/bin/env python3
"""Track sprint velocity from completed sprints.

Fetches completed issues from a sprint, calculates story points and throughput,
and reports velocity metrics for sprint planning.

Usage:
    # Track a completed sprint (by ID)
    python velocity_tracker.py --sprint-id 607

    # Track by sprint name
    python velocity_tracker.py --sprint-name "{{PROJECT_KEY}} Sprint-31"


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

_CLAUDE_DIR = Path(__file__).parent.parent.parent.parent / ".claude"
LEAN_CONFIG_PATH = _CLAUDE_DIR / "project-config.json"


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
    """Load project config."""
    with open(LEAN_CONFIG_PATH) as f:
        return json.load(f)


def get_sprint_info(api: JiraAPI, board_id: int, sprint_id: int) -> dict | None:
    """Get sprint details by ID."""
    try:
        result = api._request("GET", f"/rest/agile/1.0/sprint/{sprint_id}")
        return result
    except APIError:
        return None


def find_sprint_by_name(api: JiraAPI, board_id: int, name: str) -> dict | None:
    """Find sprint by name across all states (single API call)."""
    try:
        result = api.get_board_sprints(board_id, state="closed,active,future")
        for sprint in result.get("values", []):
            if sprint["name"] == name:
                return sprint
    except APIError:
        pass
    return None


def get_completed_issues(api: JiraAPI, sprint_id: int, sp_field: str) -> list[dict]:
    """Get all completed issues in a sprint with story points."""
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






def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate and report sprint velocity metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sprint-id", type=int, help="Sprint ID to analyze")
    group.add_argument("--sprint-name", help="Sprint name to analyze (e.g., '{{PROJECT_KEY}} Sprint-31')")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    lean = load_config()
    sp_field = lean["jira"]["custom_fields"]["story_points"]

    # Create API client
    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 2

    board_id = lean["jira"]["board_id"]

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
    issues = get_completed_issues(api, sprint_id, sp_field)

    if not issues:
        print("No completed issues found.")
        return 0

    # Calculate velocity
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
