#!/usr/bin/env python3
"""Update Confluence Page with raw storage format.

This script updates a Confluence page using raw storage format,
allowing for proper macro support (ToC, Children, etc.)

Example usage:
    python update_page_storage.py --page-id 222333444 --content-file content.html
    python update_page_storage.py --page-id 222333444 --content "<h1>Title</h1><p>Content</p>"
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
        description="Update Confluence page with raw storage format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update from file
  python update_page_storage.py --page-id 222333444 --content-file content.html

  # Update with inline content
  python update_page_storage.py --page-id 222333444 --content "<h1>Title</h1>"

  # Dry run (preview only)
  python update_page_storage.py --page-id 222333444 --content-file content.html --dry-run
        """,
    )

    parser.add_argument("--page-id", required=True, help="Page ID to update")
    parser.add_argument("--content", help="Raw storage format content (inline)")
    parser.add_argument("--content-file", help="Path to file with storage format content")
    parser.add_argument("--title", help="New title (optional, keeps existing if not specified)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get content
    if args.content_file:
        try:
            with open(args.content_file, encoding="utf-8") as f:
                storage_content = f.read()
        except OSError as e:
            logger.error("Failed to read content file: %s", e)
            return 1
    elif args.content:
        storage_content = args.content
    else:
        logger.error("Specify --content or --content-file")
        return 1

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 1

    try:
        # Get current page info
        page = api.get_page(args.page_id)
        title = args.title or page["title"]
        version = page["version"]["number"]

        print(f"📄 Page: {title}")
        print(f"   ID: {args.page_id}")
        print(f"   Current version: {version}")

        if args.dry_run:
            print("\n🔍 DRY RUN - Storage content preview:")
            print("=" * 60)
            print(storage_content[:500])
            if len(storage_content) > 500:
                print(f"... ({len(storage_content) - 500} more characters)")
            print("=" * 60)
            return 0

        # Update the page
        result = api.update_page(args.page_id, title, storage_content, version)
        print(f"✅ Updated to version {result['version']['number']}")
        print(f"   URL: {api.get_page_url(args.page_id)}")

        return 0

    except PageNotFoundError:
        logger.error("Page not found: %s", args.page_id)
        return 1
    except APIError as e:
        logger.error("API Error: %s - %s", e.status_code, e.reason)
        if e.details:
            print(f"Details: {e.details[:500]}")
        return 1
    except Exception as e:
        logger.error("Error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
