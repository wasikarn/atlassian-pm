#!/usr/bin/env python3
"""Update Jira issue descriptions via ADF text replacement.

Uses Jira REST API v3 to manipulate ADF (Atlassian Document Format) directly,
preserving all formatting (panels, tables, marks, code blocks, etc.)

Usage:
    # From JSON config
    python update_jira_description.py --config fixes.json

    # Single issue with inline replacements
    python update_jira_description.py --issue BEP-2819 \
        --find "billboard_ids" --replace "billboard_codes"

    # Multiple replacements for single issue
    python update_jira_description.py --issue BEP-2819 \
        --find "old1" --replace "new1" \
        --find "old2" --replace "new2"

    # Dry run (preview only)
    python update_jira_description.py --config fixes.json --dry-run

Config JSON format:
    {
        "BEP-2819": [
            ["billboard_ids", "billboard_codes"]
        ],
        "BEP-2755": [
            ["old text", "new text"],
            ["another old", "another new"]
        ]
    }
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
    IssueNotFoundError,
    JiraAPI,
    create_ssl_context,
    derive_jira_url,
    get_auth_header,
    load_credentials,
)

# Configure logging
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


def load_config(config_path: str) -> dict[str, list[tuple[str, str]]]:
    """Load fix config from JSON file.

    Expected format:
    {
        "BEP-2819": [
            ["old_text", "new_text"],
            ["another_old", "another_new"]
        ]
    }

    Returns:
        Dict mapping issue keys to lists of (find, replace) tuples.
    """
    with open(config_path) as f:
        raw = json.load(f)

    fixes: dict[str, list[tuple[str, str]]] = {}
    for issue_key, replacements in raw.items():
        fixes[issue_key] = [(r[0], r[1]) for r in replacements]

    return fixes


def process_issue(
    api: JiraAPI,
    issue_key: str,
    replacements: list[tuple[str, str]],
    dry_run: bool = False,
) -> str:
    """Process a single issue. Returns status string."""
    print(f"\n{'=' * 60}")
    print(f"Processing: {issue_key}")
    print("=" * 60)

    try:
        had_changes, count = api.fix_description(issue_key, replacements, dry_run=dry_run)
    except IssueNotFoundError:
        print(f"  Issue not found: {issue_key}")
        return "failed"
    except APIError as e:
        print(f"  API Error {e.status_code}: {e.reason}")
        return "failed"

    if not had_changes:
        print("  No matches found — already correct or text differs")
        for old, _new in replacements:
            print(f'    Looking for: "{old[:60]}"')
        return "skipped"

    print(f"  Found {count} replacement(s):")
    for old, new in replacements:
        print(f'    "{old[:50]}" -> "{new[:50]}"')

    if dry_run:
        print("  DRY RUN — no changes applied")
    else:
        print("  Updated successfully")

    return "success"


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update Jira issue descriptions via ADF text replacement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix from JSON config
  python update_jira_description.py --config fixes.json

  # Fix single issue
  python update_jira_description.py --issue BEP-2819 \\
      --find "billboard_ids" --replace "billboard_codes"

  # Dry run
  python update_jira_description.py --config fixes.json --dry-run

Config JSON format:
  {
    "BEP-2819": [["old_text", "new_text"]],
    "BEP-2755": [["old1", "new1"], ["old2", "new2"]]
  }
        """,
    )

    parser.add_argument("--config", help="Path to JSON config file with fix definitions")
    parser.add_argument("--issue", help="Single issue key to fix (e.g., BEP-2819)")
    parser.add_argument(
        "--find",
        action="append",
        default=[],
        help="Text to find (use with --issue, repeatable)",
    )
    parser.add_argument(
        "--replace",
        action="append",
        default=[],
        help="Replacement text (use with --issue, repeatable)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.config and not args.issue:
        parser.error("Either --config or --issue is required")

    if args.issue and len(args.find) != len(args.replace):
        parser.error("--find and --replace must be provided in pairs")

    if args.issue and not args.find:
        parser.error("--find/--replace required with --issue")

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 1

    # Build fix definitions
    fixes: dict[str, list[tuple[str, str]]] = {}

    if args.config:
        fixes = load_config(args.config)
    elif args.issue:
        fixes = {args.issue: list(zip(args.find, args.replace, strict=True))}

    # Process
    print("=" * 60)
    print(f"Jira Description Updater ({len(fixes)} issue(s))")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)

    results = {"success": 0, "skipped": 0, "failed": 0}

    for issue_key, replacements in fixes.items():
        status = process_issue(api, issue_key, replacements, args.dry_run)
        results[status] += 1

    # Summary
    print(f"\n{'=' * 60}")
    total = sum(results.values())
    print(
        f"Summary: {results['success']} updated, {results['skipped']} skipped, {results['failed']} failed (of {total})"
    )
    print("=" * 60)

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
