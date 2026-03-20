#!/usr/bin/env python3
"""Create or Update Confluence Page with proper code block formatting.

This script converts markdown to Confluence storage format with proper
<ac:structured-macro> tags for code blocks.

Example usage:
    # Create new page
    python create_confluence_page.py --space BEP --title "My Page" --content-file content.md

    # Create as child of parent page
    python create_confluence_page.py --space BEP --title "My Page" --parent-id 123456 --content-file content.md

    # Update existing page
    python create_confluence_page.py --page-id 123456 --content-file content.md

    # Update with inline content
    python create_confluence_page.py --page-id 123456 --content "# Hello World"
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
    ContentConversionError,
    CredentialsError,
    PageNotFoundError,
    create_ssl_context,
    get_auth_header,
    load_credentials,
    markdown_to_storage,
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
        description="Create or update Confluence page with proper code formatting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create new page
  python create_confluence_page.py --space BEP --title "API Spec" --content-file spec.md

  # Create as child page
  python create_confluence_page.py --space BEP --title "Sub Page" --parent-id 123456 --content-file content.md

  # Update existing page
  python create_confluence_page.py --page-id 123456 --content-file updated.md

  # Update with inline content
  python create_confluence_page.py --page-id 123456 --content "# Updated Title"

  # Dry run (preview storage format)
  python create_confluence_page.py --space BEP --title "Test" --content "# Hello" --dry-run
        """,
    )

    # Create mode arguments
    parser.add_argument("--space", help="Space key for new page (e.g., BEP)")
    parser.add_argument("--title", help="Page title")
    parser.add_argument("--parent-id", help="Parent page ID for new page")

    # Update mode arguments
    parser.add_argument("--page-id", help="Page ID to update")

    # Content arguments
    parser.add_argument("--content", help="Markdown content (inline)")
    parser.add_argument("--content-file", help="Path to markdown file")

    # Options
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments and determine mode
    if args.page_id:
        mode = "update"
    elif args.space and args.title:
        mode = "create"
    else:
        logger.error("Specify either --page-id (update) or --space and --title (create)")
        return 1

    # Get content
    if args.content_file:
        try:
            with open(args.content_file, encoding="utf-8") as f:
                markdown_content = f.read()
        except OSError as e:
            logger.error("Failed to read content file: %s", e)
            return 1
    elif args.content:
        markdown_content = args.content
    else:
        logger.error("Specify --content or --content-file")
        return 1

    # Convert markdown to storage format
    try:
        storage_content = markdown_to_storage(markdown_content)
    except ContentConversionError as e:
        logger.error("Content conversion failed: %s", e)
        return 1

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN - Storage Format Preview:")
        print("=" * 60)
        print(storage_content)
        print("=" * 60)
        return 0

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 1

    try:
        if mode == "create":
            print(f"Creating page: {args.title} in space {args.space}")
            result = api.create_page(args.space, args.title, storage_content, args.parent_id)
            print(f"✅ Created: {result['title']}")
            print(f"   ID: {result['id']}")
            print(f"   URL: {api.get_page_url(result['id'])}")

        else:  # update
            # Get current page info
            page = api.get_page(args.page_id)
            title = args.title or page["title"]
            version = page["version"]["number"]

            print(f"Updating page: {title} (ID: {args.page_id})")
            print(f"Current version: {version}")

            result = api.update_page(args.page_id, title, storage_content, version)
            print(f"✅ Updated to version {result['version']['number']}")
            print(f"   URL: {api.get_page_url(args.page_id)}")

        return 0

    except PageNotFoundError as e:
        logger.error("Page not found: %s", e.page_id)
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
