#!/usr/bin/env python3
"""Generic Confluence Page Updater using REST API.

Used for updating page content with find/replace operations, and for
inserting new content after a named section heading.

Example usage:
    python update_confluence_page.py --page-id 111222333 --find "5 minutes" --replace "3 minutes"
    python update_confluence_page.py --page-id 111222333 --find "300" --replace "180" --dry-run
    python update_confluence_page.py --page-id 111222333 \\
        --insert-after-section "Overview" --content "<p>New paragraph</p>"
    python update_confluence_page.py --page-id 111222333 \\
        --insert-after-section "Overview" --content "<p>New paragraph</p>" --dry-run
"""

import argparse
import html
import logging
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

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


def create_api(retry_on_conflict: bool = True) -> ConfluenceAPI:
    """Create configured Confluence API client."""
    creds = load_credentials()
    return ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
        retry_on_conflict=retry_on_conflict,
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


def _extract_heading_text(element: ET.Element) -> str:
    """Extract plain text from a heading element (strips XML tags)."""
    return "".join(element.itertext()).strip()


def insert_after_section(
    storage_xml: str,
    section_name: str,
    insert_content: str,
    raw: bool = False,
) -> str:
    """Insert content immediately after the first block following a named heading.

    Parses Confluence storage XML (XHTML-based), locates the first heading
    whose text matches ``section_name`` (exact first, case-insensitive fallback),
    then inserts ``insert_content`` after the heading's immediately following
    sibling block element.

    Args:
        storage_xml: Confluence page body in storage format.
        section_name: Heading text to search for (h1-h4).
        insert_content: HTML/XML snippet to insert.
        raw: If True, insert content as-is without wrapping in ``<p>``.

    Returns:
        Modified storage XML string.

    Raises:
        ValueError: If the section is not found. The error message lists
            fuzzy-matched candidate heading texts.
    """
    # Wrap in a root element so ElementTree can parse fragment XML
    wrapped = f"<root>{storage_xml}</root>"
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError as exc:
        raise ValueError(f"Failed to parse storage XML: {exc}") from exc

    heading_tags = {"h1", "h2", "h3", "h4"}
    children = list(root)

    # Collect all headings for fuzzy suggestions on failure
    all_headings: list[str] = [
        _extract_heading_text(el) for el in children if el.tag in heading_tags
    ]

    # --- locate target heading ---
    target_idx: int | None = None

    # Exact match first
    for idx, el in enumerate(children):
        if el.tag in heading_tags and _extract_heading_text(el) == section_name:
            target_idx = idx
            break

    # Case-insensitive fallback
    if target_idx is None:
        lower_name = section_name.lower()
        for idx, el in enumerate(children):
            if el.tag in heading_tags and _extract_heading_text(el).lower() == lower_name:
                target_idx = idx
                break

    if target_idx is None:
        # Build fuzzy suggestions (headings that share at least one word)
        name_words = set(section_name.lower().split())
        suggestions = [
            h for h in all_headings if name_words & set(h.lower().split())
        ]
        suggestion_hint = ""
        if suggestions:
            quoted = ", ".join(f'"{s}"' for s in suggestions[:5])
            suggestion_hint = f" Did you mean: {quoted}?"
        raise ValueError(
            f"Section '{section_name}' not found in page headings.{suggestion_hint}"
            f" Available headings: {all_headings}"
        )

    # Determine insertion index: after the heading's next sibling block, or right
    # after the heading if it is the last child
    insert_idx = target_idx + 1
    if insert_idx < len(children):
        # Skip the immediately following block (we insert after it)
        insert_idx += 1

    # Build the element to insert
    if raw:
        # Parse raw XML snippet
        try:
            new_el = ET.fromstring(insert_content)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid raw XML content: {exc}") from exc
    else:
        new_el = ET.fromstring(f"<p>{html.escape(insert_content)}</p>")

    root.insert(insert_idx, new_el)

    # Serialise back — strip the wrapper <root> tags
    serialised = ET.tostring(root, encoding="unicode")
    # Remove <root> and </root> wrapper
    serialised = serialised.removeprefix("<root>").removesuffix("</root>")
    return serialised


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
            print("DRY RUN - no changes applied")
            return True

        # Update page
        result = api.update_page(page_id, title, new_content, version)
        print(f"Updated to version {result['version']['number']}")

        return True

    except PageNotFoundError:
        print(f"Page not found: {page_id}")
        return False
    except APIError as e:
        print(f"API Error: {e.status_code} - {e.reason}")
        if e.details:
            print(f"Details: {e.details[:500]}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def process_insert_after_section(
    api: ConfluenceAPI,
    page_id: str,
    section_name: str,
    content: str,
    raw: bool = False,
    dry_run: bool = False,
) -> bool:
    """Insert content after a named section heading on a Confluence page.

    Args:
        api: Confluence API client
        page_id: Confluence page ID
        section_name: Heading text to locate (h1-h4)
        content: Content to insert (wrapped in <p> unless --raw)
        raw: Pass content as raw XML/HTML without wrapping
        dry_run: If True, print the planned insertion without writing

    Returns:
        True on success (or dry-run preview), False on error.
    """
    print(f"\n{'=' * 60}")
    print(f"Insert-after-section on page ID: {page_id}")
    print("=" * 60)

    try:
        page = api.get_page(page_id)
        title = page["title"]
        current_content = page["body"]["storage"]["value"]
        version = page["version"]["number"]

        print(f"Title: {title}")
        print(f"Current version: {version}")
        print(f"Section: '{section_name}'")

        new_content = insert_after_section(current_content, section_name, content, raw=raw)

        if dry_run:
            print("DRY RUN - planned insertion (diff excerpt):")
            print("=" * 60)
            # Show the new content snippet around the insertion point
            idx = new_content.find(content if raw else content[:30])
            start = max(0, idx - 120)
            end = min(len(new_content), idx + len(content) + 120)
            print(f"...{new_content[start:end]}...")
            print("=" * 60)
            return True

        result = api.update_page(page_id, title, new_content, version)
        print(f"Updated to version {result['version']['number']}")
        return True

    except ValueError as e:
        print(f"Error: {e}")
        return False
    except PageNotFoundError:
        print(f"Page not found: {page_id}")
        return False
    except APIError as e:
        print(f"API Error: {e.status_code} - {e.reason}")
        if e.details:
            print(f"Details: {e.details[:500]}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update Confluence page content with find/replace operations or section insertion",
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

  # Insert after section heading
  python update_confluence_page.py --page-id 111222333 \\
    --insert-after-section "Overview" --content "New information here"

  # Insert raw XML/HTML after section (no <p> wrapping)
  python update_confluence_page.py --page-id 111222333 \\
    --insert-after-section "Overview" --content "<ul><li>item</li></ul>" --raw

  # Disable 409 retry (default: retry once on version conflict)
  python update_confluence_page.py --page-id 111222333 --find "old" --replace "new" \\
    --no-retry-on-conflict
        """,
    )

    parser.add_argument("--page-id", required=True, help="Confluence page ID")

    # find/replace group
    parser.add_argument("--find", action="append", default=[], help="Text to find (can specify multiple)")
    parser.add_argument("--replace", action="append", default=[], help="Replacement text (must match --find count)")
    parser.add_argument("--regex", action="store_true", help="Treat find patterns as regex")

    # insert-after-section group
    parser.add_argument("--insert-after-section", metavar="SECTION_NAME", help="Heading text to insert after")
    parser.add_argument(
        "--content",
        metavar="CONTENT",
        help="Content to insert (used with --insert-after-section)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Pass --content as raw XML/HTML without wrapping in <p>",
    )

    # shared flags
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--no-retry-on-conflict",
        action="store_true",
        default=False,
        help="Disable automatic retry on HTTP 409 version conflict (default: retry once)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate mode
    if args.insert_after_section:
        if not args.content:
            parser.error("--content is required when using --insert-after-section")
        if args.find:
            parser.error("--find/--replace cannot be combined with --insert-after-section")
    else:
        if not args.find:
            parser.error("Either --find/--replace or --insert-after-section is required")
        if len(args.find) != len(args.replace):
            logger.error("Number of --find and --replace arguments must match")
            return 1

    try:
        api = create_api(retry_on_conflict=not args.no_retry_on_conflict)
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 1

    if args.insert_after_section:
        success = process_insert_after_section(
            api,
            args.page_id,
            args.insert_after_section,
            args.content,
            raw=args.raw,
            dry_run=args.dry_run,
        )
    else:
        # Build replacements list
        replacements = [(f, r, args.regex) for f, r in zip(args.find, args.replace, strict=True)]
        success = process_page(api, args.page_id, replacements, args.dry_run)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
