#!/usr/bin/env python3
"""Generic Confluence Page Updater using REST API.

Used for updating page content with find/replace operations.

Example usage:
    python update_confluence_page.py --page-id 111222333 --find "5 minutes" --replace "3 minutes"
    python update_confluence_page.py --page-id 111222333 --find "300" --replace "180" --dry-run
"""

import argparse
import logging
import re
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


def find_and_replace(
    content: str,
    find_text: str,
    replace_text: str,
    use_regex: bool = False,
) -> tuple[str, int]:
    """Find and replace text in content.

    Args:
        content: Content to search
        find_text: Text or pattern to find
        replace_text: Replacement text
        use_regex: If True, treat find_text as regex pattern

    Returns:
        Tuple of (new_content, replacement_count)
    """
    if use_regex:
        pattern = re.compile(find_text)
        new_content, count = pattern.subn(replace_text, content)
    else:
        count = content.count(find_text)
        new_content = content.replace(find_text, replace_text)

    return new_content, count


def process_page(
    api: ConfluenceAPI,
    page_id: str,
    replacements: list[tuple[str, str, bool]],
    dry_run: bool = False,
) -> bool:
    """Process a single page with multiple find/replace operations.

    Args:
        api: Confluence API client
        page_id: Confluence page ID
        replacements: List of (find, replace, use_regex) tuples
        dry_run: If True, only show what would be changed

    Returns:
        True if changes were made (or would be made in dry run), False otherwise.
    """
    print(f"\n{'=' * 60}")
    print(f"Processing page ID: {page_id}")
    print("=" * 60)

    try:
        # Get current page
        page = api.get_page(page_id)
        title = page["title"]
        current_content = page["body"]["storage"]["value"]
        version = page["version"]["number"]

        print(f"Title: {title}")
        print(f"Current version: {version}")

        # Apply all replacements
        new_content = current_content
        total_changes = 0

        for find_text, replace_text, use_regex in replacements:
            new_content, count = find_and_replace(new_content, find_text, replace_text, use_regex)
            if count > 0:
                print(f"  '{find_text}' → '{replace_text}': {count} replacement(s)")
                total_changes += count

        if total_changes == 0:
            print("No matches found - no changes needed")
            return False

        print(f"Total changes: {total_changes}")

        if dry_run:
            print("🔍 DRY RUN - no changes applied")
            return True

        # Update page
        result = api.update_page(page_id, title, new_content, version)
        print(f"✅ Updated to version {result['version']['number']}")

        return True

    except PageNotFoundError:
        print(f"❌ Page not found: {page_id}")
        return False
    except APIError as e:
        print(f"❌ API Error: {e.status_code} - {e.reason}")
        if e.details:
            print(f"Details: {e.details[:500]}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update Confluence page content with find/replace operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple text replacement
  python update_confluence_page.py --page-id 111222333 --find "5 minutes" --replace "3 minutes"

  # Multiple replacements
  python update_confluence_page.py --page-id 111222333 \\
    --find "5 minutes" --replace "3 minutes" \\
    --find "300" --replace "180"

  # Dry run (preview changes)
  python update_confluence_page.py --page-id 111222333 --find "old" --replace "new" --dry-run

  # Regex replacement
  python update_confluence_page.py --page-id 111222333 --find "v\\d+\\.\\d+" --replace "v2.0" --regex
        """,
    )

    parser.add_argument("--page-id", required=True, help="Confluence page ID")
    parser.add_argument("--find", action="append", required=True, help="Text to find (can specify multiple)")
    parser.add_argument("--replace", action="append", required=True, help="Replacement text (must match --find count)")
    parser.add_argument("--regex", action="store_true", help="Treat find patterns as regex")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if len(args.find) != len(args.replace):
        logger.error("Number of --find and --replace arguments must match")
        return 1

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 1

    # Build replacements list
    replacements = [(f, r, args.regex) for f, r in zip(args.find, args.replace, strict=True)]

    # Process page
    success = process_page(api, args.page_id, replacements, args.dry_run)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
