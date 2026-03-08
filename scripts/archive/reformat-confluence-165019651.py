#!/usr/bin/env python3
"""Reformat Confluence page 165019651 (Redis Sorted Set: 4 Optimization Tickets).

Fixes:
1. Add ToC macro at top for navigation
2. Fix <p> wrapping around metadata table
3. Remove trailing empty <p></p>

One-time script — idempotent (checks for existing ToC).
"""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts")
)
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib import ConfluenceAPI

TOC_MACRO = (
    '<ac:structured-macro ac:name="toc" ac:schema-version="1">'
    '<ac:parameter ac:name="minLevel">2</ac:parameter>'
    "</ac:structured-macro>\n"
)

PAGE_ID = "165019651"


def main():
    dry_run = "--dry-run" in sys.argv

    creds = load_credentials()
    api = ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(
            creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]
        ),
        ssl_context=create_ssl_context(),
    )

    page = api.get_page(PAGE_ID)
    content = page["body"]["storage"]["value"]
    version = page["version"]["number"]
    title = page["title"]

    print(f"=== Reformatting Confluence page: {title} ===")

    # Idempotency check
    if 'ac:name="toc"' in content:
        print("  ToC already present — skipping")
        return

    changes = []

    # 1. Fix <p> wrapping around metadata table
    if content.startswith("<p><table>"):
        content = content.replace("<p><table>", "<table>", 1)
        # Find the matching close: </table>\n<hr/>\n</p>
        content = content.replace(
            "</table>\n<hr/>\n</p>", "</table>\n<hr/>", 1
        )
        changes.append("Fixed <p> wrapping around metadata table")

    # 2. Remove trailing empty <p></p>
    if content.rstrip().endswith("<p></p>"):
        content = content.rstrip()
        content = content[: content.rfind("<p></p>")]
        changes.append("Removed trailing empty <p></p>")

    # 3. Prepend ToC macro
    content = TOC_MACRO + content
    changes.append("Added ToC macro")

    if dry_run:
        print(f"  DRY RUN — {len(changes)} changes:")
        for c in changes:
            print(f"    - {c}")
        print(f"  Content preview: {content[:200]}...")
        return

    result = api.update_page(PAGE_ID, title, content, version)
    new_version = result["version"]["number"]
    print(f"  Updated to v{new_version}")
    for c in changes:
        print(f"    - {c}")


if __name__ == "__main__":
    main()
