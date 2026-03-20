#!/usr/bin/env python3
"""Set parent (Epic) on Jira issues via REST API v3.

MCP tools and acli cannot reliably set the parent field on existing issues.
This script uses the Jira REST API v3 directly to set/change/remove the parent.

Usage:
    # Set parent on single issue
    python jira_set_parent.py --issues BEP-3331 --parent BEP-3197

    # Set parent on multiple issues
    python jira_set_parent.py --issues BEP-3331,BEP-3332,BEP-3333 --parent BEP-3197

    # Remove parent from issues
    python jira_set_parent.py --issues BEP-3331 --remove

    # Dry run (verify current parent, no writes)
    python jira_set_parent.py --issues BEP-3331,BEP-3332 --parent BEP-3197 --dry-run

    # Verbose output
    python jira_set_parent.py --issues BEP-3331 --parent BEP-3197 -v

Exit codes:
    0 = all updates succeeded
    1 = some updates failed
    2 = error (input/credentials)
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import (
    APIError,
    CredentialsError,
    IssueNotFoundError,
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


def create_api() -> JiraAPI:
    """Create configured Jira API client."""
    creds = load_credentials()
    jira_url = derive_jira_url(creds["CONFLUENCE_URL"])
    return JiraAPI(
        base_url=jira_url,
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )


def get_current_parent(api: JiraAPI, issue_key: str) -> str | None:
    """Get current parent key for an issue."""
    issue = api.get_issue(issue_key, fields="parent,summary")
    parent = issue["fields"].get("parent")
    return parent.get("key") if parent else None


def set_parent(api: JiraAPI, issue_key: str, parent_key: str | None, dry_run: bool = False) -> bool:
    """Set or remove parent on a Jira issue.

    Args:
        api: Jira API client
        issue_key: Issue to update
        parent_key: Parent issue key, or None to remove parent
        dry_run: If True, only show current state without updating

    Returns:
        True if successful (or dry run), False on failure.
    """
    try:
        current_parent = get_current_parent(api, issue_key)
    except IssueNotFoundError:
        print(f"  {issue_key}: \u274c issue not found")
        return False
    except APIError as e:
        print(f"  {issue_key}: \u274c failed to read — {e.status_code} {e.reason}")
        return False

    # Check if already set correctly
    if parent_key and current_parent == parent_key:
        print(f"  {issue_key}: \u2705 already has parent {parent_key}")
        return True

    if not parent_key and current_parent is None:
        print(f"  {issue_key}: \u2705 already has no parent")
        return True

    action = f"→ {parent_key}" if parent_key else "→ (none)"
    current = current_parent or "(none)"

    if dry_run:
        print(f"  {issue_key}: {current} {action} (dry run)")
        return True

    # Build update payload
    parent_value = {"key": parent_key} if parent_key else None
    try:
        api.update_fields(issue_key, {"parent": parent_value})
        print(f"  {issue_key}: {current} {action} \u2705")
        return True
    except APIError as e:
        print(f"  {issue_key}: \u274c {e.status_code} {e.reason}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set parent (Epic) on Jira issues via REST API v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--issues", "-i",
        required=True,
        help="Comma-separated issue keys (e.g., BEP-3331,BEP-3332)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--parent", "-p",
        help="Parent issue key to set (e.g., BEP-3197)",
    )
    group.add_argument(
        "--remove",
        action="store_true",
        help="Remove parent from issues",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show current state, no writes")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    issue_keys = [k.strip() for k in args.issues.split(",") if k.strip()]
    parent_key = args.parent if not args.remove else None

    if not issue_keys:
        logger.error("No issue keys provided")
        return 2

    action = f"Set parent → {parent_key}" if parent_key else "Remove parent"
    print(f"{'=' * 50}")
    print(f"{action} ({len(issue_keys)} issue{'s' if len(issue_keys) > 1 else ''})")
    if args.dry_run:
        print("  (DRY RUN)")
    print(f"{'=' * 50}")

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 2

    success = 0
    for key in issue_keys:
        if set_parent(api, key, parent_key, args.dry_run):
            success += 1

    print(f"\n{'=' * 50}")
    total = len(issue_keys)
    if success == total:
        print(f"\u2705 All {total} issue{'s' if total > 1 else ''} updated")
        return 0
    else:
        print(f"\u26a0\ufe0f {success}/{total} succeeded, {total - success} failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
