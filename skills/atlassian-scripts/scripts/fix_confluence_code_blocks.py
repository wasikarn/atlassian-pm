#!/usr/bin/env python3
"""Fix Confluence code blocks to proper macro format.

This script converts HTML code blocks from:
    <pre class="highlight"><code class="language-xxx">...</code></pre>
To:
    <ac:structured-macro ac:name="code">...</ac:structured-macro>

Example usage:
    python fix_confluence_code_blocks.py --page-id 123456789
    python fix_confluence_code_blocks.py --page-ids 123456789,333444555 --dry-run
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
    fix_code_blocks,
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


def process_page(api: ConfluenceAPI, page_id: str, dry_run: bool = False) -> bool:
    """Process a single page to fix code blocks.

    Args:
        api: Confluence API client
        page_id: Page ID to process
        dry_run: If True, only preview changes

    Returns:
        True if page was fixed or would be fixed (dry run), False otherwise.
    """
    try:
        # Get current page
        page = api.get_page(page_id)
        title = page["title"]
        current_content = page["body"]["storage"]["value"]
        version = page["version"]["number"]

        print(f"\n📄 {title}")
        print(f"   ID: {page_id}")
        print(f"   Current version: {version}")

        # Check if needs fixing
        if '<pre class="highlight">' not in current_content:
            print("   ⏭️ No code blocks need fixing (already using structured macros)")
            return False

        # Count blocks that need fixing
        original_count = current_content.count('<pre class="highlight">')
        print(f"   Found {original_count} code block(s) that need fixing...")

        # Fix code blocks
        fixed_content = fix_code_blocks(current_content)

        if dry_run:
            print("   🔍 DRY RUN - no changes applied")
            return True

        # Update page
        result = api.update_page(page_id, title, fixed_content, version)
        print(f"   ✅ Fixed {original_count} code blocks, updated to version {result['version']['number']}")

        return True

    except PageNotFoundError:
        print(f"   ❌ Page not found: {page_id}")
        return False
    except APIError as e:
        print(f"   ❌ API Error: {e.status_code} - {e.reason}")
        if e.details:
            print(f"      Details: {e.details[:200]}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix Confluence code blocks to proper macro format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix single page
  python fix_confluence_code_blocks.py --page-id 123456789

  # Fix multiple pages
  python fix_confluence_code_blocks.py --page-ids 123456789,333444555,444555666

  # Dry run (preview only)
  python fix_confluence_code_blocks.py --page-ids 123456789,333444555 --dry-run
        """,
    )

    parser.add_argument("--page-id", help="Single page ID to fix")
    parser.add_argument("--page-ids", help="Comma-separated list of page IDs to fix")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get list of pages to process
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

    print("Confluence Code Block Fixer")
    print("=" * 60)
    print(f"Processing {len(page_ids)} page(s)...")

    fixed_count = 0
    skipped_count = 0

    for page_id in page_ids:
        result = process_page(api, page_id, args.dry_run)
        if result:
            fixed_count += 1
        else:
            skipped_count += 1

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    if args.dry_run:
        print(f"Would fix: {fixed_count}, Already OK: {skipped_count}")
    else:
        print(f"Fixed: {fixed_count}, Skipped: {skipped_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
