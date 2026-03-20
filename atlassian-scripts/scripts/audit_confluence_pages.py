#!/usr/bin/env python3
"""Audit Confluence pages for expected/unexpected content.

Checks multiple pages against should_have / should_not_have rules.
Useful for alignment verification across documentation.

Example usage:
    # Audit from JSON config
    python audit_confluence_pages.py --config audit.json

    # Audit single page
    python audit_confluence_pages.py --page-id 987654321 \
        --should-have "BEP-2883" "2026" \
        --should-not-have "2025-01-21"

    # Dry run (just check, no changes)
    python audit_confluence_pages.py --config audit.json --verbose
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


def audit_page(
    api: ConfluenceAPI,
    page_id: str,
    label: str,
    should_have: list[str],
    should_not_have: list[str],
) -> tuple[bool, list[str]]:
    """Audit a single page for expected/unexpected content.

    Args:
        api: Confluence API client
        page_id: Confluence page ID
        label: Human-readable label for the page
        should_have: List of strings that MUST be present
        should_not_have: List of strings that MUST NOT be present

    Returns:
        Tuple of (passed, issues_list)
    """
    try:
        page = api.get_page(page_id)
    except PageNotFoundError:
        return False, [f"Page not found: {page_id}"]
    except APIError as e:
        return False, [f"API Error {e.status_code}: {e.reason}"]

    content = page["body"]["storage"]["value"]
    version = page["version"]["number"]
    title = page["title"]

    issues: list[str] = []

    for term in should_have:
        if term not in content:
            issues.append(f'MISSING: "{term}"')

    for term in should_not_have:
        if term in content:
            issues.append(f'STILL HAS: "{term}"')

    passed = len(issues) == 0
    status = "✅ PASS" if passed else "❌ FAIL"

    print(f"\n{status} {label} (Page {page_id}, v{version})")
    print(f"  Title: {title}")

    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        checks = len(should_have) + len(should_not_have)
        print(f"  All {checks} checks passed")

    return passed, issues


def load_config(config_path: str) -> list[dict]:
    """Load audit config from JSON file.

    Expected format:
    [
        {
            "page_id": "987654321",
            "label": "Epic Parent Page",
            "should_have": ["BEP-2883", "2026"],
            "should_not_have": ["2025-01-21"]
        }
    ]
    """
    with open(config_path) as f:
        return json.load(f)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Audit Confluence pages for expected/unexpected content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Audit from JSON config
  python audit_confluence_pages.py --config audit.json

  # Audit single page
  python audit_confluence_pages.py --page-id 987654321 \\
      --should-have "BEP-2883" "2026" \\
      --should-not-have "2025-01-21"

Config JSON format:
  [
    {
      "page_id": "987654321",
      "label": "Epic Parent Page",
      "should_have": ["BEP-2883"],
      "should_not_have": ["2025"]
    }
  ]
        """,
    )

    parser.add_argument("--config", help="Path to JSON config file with audit rules")
    parser.add_argument("--page-id", help="Single page ID to audit")
    parser.add_argument("--label", default="Page", help="Label for the page (used with --page-id)")
    parser.add_argument(
        "--should-have",
        nargs="+",
        default=[],
        help="Strings that MUST be present in the page",
    )
    parser.add_argument(
        "--should-not-have",
        nargs="+",
        default=[],
        help="Strings that MUST NOT be present in the page",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.config and not args.page_id:
        parser.error("Either --config or --page-id is required")

    try:
        api = create_api()
    except CredentialsError as e:
        logger.error("Credentials error: %s", e)
        return 1

    # Build audit rules
    audit_rules: list[dict] = []

    if args.config:
        audit_rules = load_config(args.config)
    elif args.page_id:
        audit_rules = [
            {
                "page_id": args.page_id,
                "label": args.label,
                "should_have": args.should_have,
                "should_not_have": args.should_not_have,
            }
        ]

    # Run audits
    print("=" * 60)
    print(f"Confluence Page Audit ({len(audit_rules)} pages)")
    print("=" * 60)

    total_pass = 0
    total_fail = 0

    for rule in audit_rules:
        passed, _ = audit_page(
            api=api,
            page_id=rule["page_id"],
            label=rule.get("label", f"Page {rule['page_id']}"),
            should_have=rule.get("should_have", []),
            should_not_have=rule.get("should_not_have", []),
        )
        if passed:
            total_pass += 1
        else:
            total_fail += 1

    # Summary
    print(f"\n{'=' * 60}")
    total = total_pass + total_fail
    if total_fail == 0:
        print(f"✅ ALL {total} PAGES PASSED")
    else:
        print(f"❌ {total_fail}/{total} PAGES FAILED")
    print("=" * 60)

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
