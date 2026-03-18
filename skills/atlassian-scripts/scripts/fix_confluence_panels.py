#!/usr/bin/env python3
"""Fix Confluence ADF panel conversion bug.

Confluence's storage→ADF conversion sometimes creates `bodiedExtension` nodes
instead of native `panel` for success/error/warning/note/tip macros.
This causes "Error loading the extension!" in view mode.

This script reads the page ADF via v2 API, converts broken bodiedExtension
nodes back to native panel nodes, and updates the page.

Example usage:
    python fix_confluence_panels.py --page-id 123456789
    python fix_confluence_panels.py --page-ids 123456789,333444555
    python fix_confluence_panels.py --page-id 123456789 --dry-run
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
    ConfluenceAPI,
    CredentialsError,
    PageNotFoundError,
    create_ssl_context,
    get_auth_header,
    load_credentials,
)

logger = logging.getLogger(__name__)

# Panel macro keys that Confluence should render as native ADF panels
PANEL_TYPES = {"info", "note", "warning", "error", "success", "tip"}


def fix_panels_in_adf(adf: dict) -> tuple[dict, int]:
    """Walk ADF tree and convert bodiedExtension panel nodes to native panel.

    Returns (fixed_adf, count_of_fixes).
    """
    fixed_count = 0

    def fix_node(node):
        nonlocal fixed_count
        if not isinstance(node, dict):
            return node
        # Detect broken panel: bodiedExtension with a panel-type extensionKey
        if (
            node.get("type") == "bodiedExtension"
            and node.get("attrs", {}).get("extensionKey", "") in PANEL_TYPES
            and "macro.core" in node.get("attrs", {}).get("extensionType", "")
        ):
            fixed_count += 1
            return {
                "type": "panel",
                "attrs": {"panelType": node["attrs"]["extensionKey"]},
                "content": [fix_node(c) for c in node.get("content", [])],
            }
        # Recurse into children
        if "content" in node and isinstance(node["content"], list):
            node["content"] = [fix_node(c) for c in node["content"]]
        return node

    fixed_adf = fix_node(adf)
    return fixed_adf, fixed_count


def fix_page_panels(api: ConfluenceAPI, page_id: str, dry_run: bool = False) -> int:
    """Fix ADF panel conversion bug on a single page.

    Returns number of panels fixed (0 if none needed).
    """
    # Fetch ADF via v2 API
    v2_data = api._request("GET", f"/api/v2/pages/{page_id}?body-format=atlas_doc_format")
    adf = json.loads(v2_data["body"]["atlas_doc_format"]["value"])
    title = v2_data["title"]
    ver = v2_data["version"]["number"]

    fixed_adf, fixed_count = fix_panels_in_adf(adf)

    if fixed_count == 0:
        logger.info(f"  {title} (id={page_id}): no broken panels found")
        return 0

    if dry_run:
        logger.info(f"  {title} (id={page_id}): would fix {fixed_count} panel(s) [DRY RUN]")
        return fixed_count

    # Update via v2 API with fixed ADF
    api._request(
        "PUT",
        f"/api/v2/pages/{page_id}",
        data={
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "atlas_doc_format",
                "value": json.dumps(fixed_adf),
            },
            "version": {"number": ver + 1},
        },
    )
    logger.info(f"  {title} (id={page_id}): fixed {fixed_count} panel(s) (v{ver} → v{ver + 1})")
    return fixed_count


def main():
    parser = argparse.ArgumentParser(
        description="Fix Confluence ADF panel conversion bug (bodiedExtension → native panel)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--page-id", help="Single page ID to fix")
    group.add_argument("--page-ids", help="Comma-separated page IDs to fix")
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't update pages")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    page_ids = [args.page_id] if args.page_id else [p.strip() for p in args.page_ids.split(",")]

    try:
        creds = load_credentials()
        api = ConfluenceAPI(
            base_url=creds["url"],
            auth_header=get_auth_header(creds),
            ssl_context=create_ssl_context(),
        )
    except CredentialsError as e:
        logger.error(f"Auth error: {e}")
        sys.exit(1)

    total_fixed = 0
    for pid in page_ids:
        try:
            fixed = fix_page_panels(api, pid, dry_run=args.dry_run)
            total_fixed += fixed
        except PageNotFoundError:
            logger.error(f"  Page {pid}: NOT FOUND — skipping")
        except APIError as e:
            logger.error(f"  Page {pid}: API error — {e}")

    action = "Would fix" if args.dry_run else "Fixed"
    logger.info(f"\n{action} {total_fixed} panel(s) across {len(page_ids)} page(s)")


if __name__ == "__main__":
    main()
