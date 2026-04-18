#!/usr/bin/env python3
"""Update Jira issue descriptions via ADF text replacement or section append.

Uses Jira REST API v3 to manipulate ADF (Atlassian Document Format) directly,
preserving all formatting (panels, tables, marks, code blocks, etc.)

Usage:
    # From JSON config
    python update_jira_description.py --config fixes.json

    # Single issue with inline replacements
    python update_jira_description.py --issue {{PROJECT_KEY}}-2819 \
        --find "billboard_ids" --replace "billboard_codes"

    # Multiple replacements for single issue
    python update_jira_description.py --issue {{PROJECT_KEY}}-2819 \
        --find "old1" --replace "new1" \
        --find "old2" --replace "new2"

    # Append a new section after an existing heading
    python update_jira_description.py --issue {{PROJECT_KEY}}-2819 \
        --append-section "Technical Notes" --content "New paragraph text here"

    # Dry run (preview only)
    python update_jira_description.py --config fixes.json --dry-run

Config JSON format:
    {
        "{{PROJECT_KEY}}-2819": [
            ["billboard_ids", "billboard_codes"]
        ],
        "{{PROJECT_KEY}}-2755": [
            ["old text", "new text"],
            ["another old", "another new"]
        ]
    }
"""

import argparse
import json
import logging
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

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
        "{{PROJECT_KEY}}-2819": [
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


def _extract_heading_text(node: dict[str, Any]) -> str:
    """Extract plain text from an ADF heading node."""
    texts: list[str] = []
    for child in node.get("content", []):
        if child.get("type") == "text":
            texts.append(child.get("text", ""))
    return "".join(texts).strip()


def _make_paragraph_adf(text: str) -> dict[str, Any]:
    """Build a minimal ADF paragraph node from plain text."""
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }


def append_after_section(
    description_adf: dict[str, Any],
    section_title: str,
    content_text: str,
) -> dict[str, Any]:
    """Append a paragraph ADF node after the last child block of a named section.

    Locates the first heading node whose text matches ``section_title``
    (exact first, case-insensitive fallback), then appends ``content_text``
    as a paragraph node after the section's last child block — i.e., before
    the next heading at the same or higher level, or at end of document.

    Args:
        description_adf: ADF document dict (modified in-place on a deep copy).
        section_title: Heading text to locate (case-insensitive fallback).
        content_text: Plain text to append as a paragraph node.

    Returns:
        Modified ADF document (deep copy).

    Raises:
        ValueError: If the section is not found. Error includes fuzzy suggestions.
    """
    doc = deepcopy(description_adf)
    top_content: list[dict[str, Any]] = doc.get("content", [])

    # Collect all headings for suggestions on failure
    all_headings = [
        _extract_heading_text(node)
        for node in top_content
        if node.get("type") == "heading"
    ]

    # Locate target heading — exact then case-insensitive
    target_idx: int | None = None
    for idx, node in enumerate(top_content):
        if node.get("type") == "heading" and _extract_heading_text(node) == section_title:
            target_idx = idx
            break

    if target_idx is None:
        lower_title = section_title.lower()
        for idx, node in enumerate(top_content):
            if node.get("type") == "heading" and _extract_heading_text(node).lower() == lower_title:
                target_idx = idx
                break

    if target_idx is None:
        title_words = set(section_title.lower().split())
        suggestions = [h for h in all_headings if title_words & set(h.lower().split())]
        hint = ""
        if suggestions:
            quoted = ", ".join(f'"{s}"' for s in suggestions[:5])
            hint = f" Did you mean: {quoted}?"
        raise ValueError(
            f"Section '{section_title}' not found in ADF headings.{hint}"
            f" Available headings: {all_headings}"
        )

    # Determine the heading level so we stop before a heading at same/higher level
    heading_level = top_content[target_idx].get("attrs", {}).get("level", 1)

    # Find the insertion point: after the last block belonging to this section
    insert_idx = target_idx + 1
    while insert_idx < len(top_content):
        node = top_content[insert_idx]
        if node.get("type") == "heading":
            node_level = node.get("attrs", {}).get("level", 1)
            if node_level <= heading_level:
                break
        insert_idx += 1
    # insert_idx now points to the next heading (or end of doc) — insert before it

    top_content.insert(insert_idx, _make_paragraph_adf(content_text))
    doc["content"] = top_content
    return doc


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


def process_append_section(
    api: JiraAPI,
    issue_key: str,
    section_title: str,
    content_text: str,
    dry_run: bool = False,
) -> str:
    """Append content after a named section in a Jira issue description.

    Args:
        api: JiraAPI client
        issue_key: Jira issue key
        section_title: Heading text to locate
        content_text: Plain text to append as paragraph
        dry_run: If True, preview without writing

    Returns:
        Status string: "success", "skipped", or "failed".
    """
    print(f"\n{'=' * 60}")
    print(f"Append-section on: {issue_key}")
    print("=" * 60)

    try:
        issue = api.get_issue(issue_key, fields="description,summary")
    except IssueNotFoundError:
        print(f"  Issue not found: {issue_key}")
        return "failed"
    except APIError as e:
        print(f"  API Error {e.status_code}: {e.reason}")
        return "failed"

    description = issue["fields"].get("description")
    if not description:
        print(f"  {issue_key} has no description — cannot append section")
        return "skipped"

    try:
        new_description = append_after_section(description, section_title, content_text)
    except ValueError as e:
        print(f"  Error: {e}")
        return "failed"

    if dry_run:
        print(f"  DRY RUN — would append paragraph after section '{section_title}'")
        print(f"  Content: {content_text[:100]}")
        return "success"

    try:
        api.update_description(issue_key, new_description)
    except (IssueNotFoundError, APIError) as e:
        print(f"  Failed to update: {e}")
        return "failed"

    print(f"  Appended paragraph after section '{section_title}'")
    return "success"


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update Jira issue descriptions via ADF text replacement or section append",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix from JSON config
  python update_jira_description.py --config fixes.json

  # Fix single issue
  python update_jira_description.py --issue {{PROJECT_KEY}}-2819 \\
      --find "billboard_ids" --replace "billboard_codes"

  # Append content after a section heading
  python update_jira_description.py --issue {{PROJECT_KEY}}-2819 \\
      --append-section "Technical Notes" --content "New paragraph here"

  # Dry run
  python update_jira_description.py --config fixes.json --dry-run

Config JSON format:
  {
    "{{PROJECT_KEY}}-2819": [["old_text", "new_text"]],
    "{{PROJECT_KEY}}-2755": [["old1", "new1"], ["old2", "new2"]]
  }
        """,
    )

    parser.add_argument("--config", help="Path to JSON config file with fix definitions")
    parser.add_argument("--issue", help="Single issue key to fix (e.g., {{PROJECT_KEY}}-2819)")
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
    parser.add_argument(
        "--append-section",
        metavar="SECTION_TITLE",
        help="Heading text to append content after (use with --issue and --content)",
    )
    parser.add_argument(
        "--content",
        metavar="TEXT",
        help="Plain text to append as paragraph (used with --append-section)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate mode
    if args.append_section:
        if not args.issue:
            parser.error("--issue is required with --append-section")
        if not args.content:
            parser.error("--content is required with --append-section")
        if args.find or args.config:
            parser.error("--append-section cannot be combined with --find/--replace or --config")
    else:
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

    # --- Append-section mode ---
    if args.append_section:
        status = process_append_section(
            api,
            args.issue,
            args.append_section,
            args.content,
            dry_run=args.dry_run,
        )
        return 0 if status in ("success", "skipped") else 1

    # --- Find/replace mode ---
    fixes: dict[str, list[tuple[str, str]]] = {}

    if args.config:
        fixes = load_config(args.config)
    elif args.issue:
        fixes = {args.issue: list(zip(args.find, args.replace, strict=True))}

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
