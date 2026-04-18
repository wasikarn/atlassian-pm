#!/usr/bin/env python3
"""Move Confluence Page to a new parent.

This script moves a Confluence page to be a child of another page
without modifying the page content.

Example usage:
    python move_confluence_page.py --page-id 123456789 --parent-id 987654321
    python move_confluence_page.py --page-id 123456789 --parent-id 987654321 --dry-run
    python move_confluence_page.py --page-ids 123456789,333444555 --parent-id 987654321
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import (
    APIError,
    ConfluenceAPI,
    CredentialsError,
    PageNotFoundError,
    create_ssl_context,
    get_auth_header,
    load_credentials,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_api() -> ConfluenceAPI:
    """Create configured Confluence API client."""
    creds = load_credentials()
    return ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Move Confluence page to a new parent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Move page to be child of another page
  python move_confluence_page.py --page-id 123456789 --parent-id 987654321

  # Dry run (preview only)
  python move_confluence_page.py --page-id 123456789 --parent-id 987654321 --dry-run

  # Batch move multiple pages
  python move_confluence_page.py --page-ids 123456789,333444555,444555666 --parent-id 987654321
        """,
    )

    parser.add_argument("--page-id", help="Single page ID to move")
    parser.add_argument("--page-ids", help="Comma-separated list of page IDs to move")
    parser.add_argument("--parent-id", required=True, help="Target parent page ID")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--quiet", "-q",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Suppress informational output; keep only ERROR and final status line",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg)

    # Get list of pages to move
    if args.page_ids:
        page_ids = [p.strip() for p in args.page_ids.split(",")]
    elif args.page_id:
        page_ids = [args.page_id]
    else:
        logger.error("Specify --page-id or --page-ids")
        return 1

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 1

    # Get parent page info
    try:
        parent = api.get_page(args.parent_id)
        log(f"\n📁 Target Parent: {parent['title']} (ID: {args.parent_id})")
    except PageNotFoundError:
        logger.error("Parent page not found: %s", args.parent_id)
        return 1
    except APIError as e:
        logger.error("Error getting parent page: %s", e)
        return 1

    log(f"\n{'=' * 60}")
    log(f"Moving {len(page_ids)} page(s) to parent: {parent['title']}")
    log("=" * 60)

    success_count = 0
    fail_count = 0

    for page_id in page_ids:
        try:
            # Get page info
            page = api.get_page(page_id)
            title = page["title"]
            ancestors = page.get("ancestors", [])
            current_parent = ancestors[-1].get("title", "Root") if ancestors else "Root"

            log(f"\n📄 {title}")
            log(f"   ID: {page_id}")
            log(f"   Current parent: {current_parent}")
            log(f"   → New parent: {parent['title']}")

            if args.dry_run:
                log("   🔍 DRY RUN - no changes applied")
                success_count += 1
                continue

            # Move the page
            api.move_page(page_id, args.parent_id)
            print(f"moved page_id={page_id} title={title!r} parent_id={args.parent_id}")
            success_count += 1

        except PageNotFoundError:
            print(f"ERROR page_id={page_id} reason=not_found")
            fail_count += 1
        except APIError as e:
            print(f"ERROR page_id={page_id} status={e.status_code} reason={e.reason}")
            if e.details and not args.quiet:
                print(f"      Details: {e.details[:200]}")
            fail_count += 1
        except Exception as e:
            print(f"ERROR page_id={page_id} reason={e}")
            fail_count += 1

    log(f"\n{'=' * 60}")
    print(f"summary pages={len(page_ids)} succeeded={success_count} failed={fail_count}")
    log("=" * 60)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
