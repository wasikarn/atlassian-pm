#!/usr/bin/env python3
"""Reformat Confluence page 165052419 (Coupon Daily Limit Tech Note).

Fixes:
1. Remove redundant H1 (duplicates page title)
2. Convert <blockquote> to Confluence info/note panels
3. Add numbered section pattern to H2s
4. Add ToC macro at top
5. Remove empty <p></p> elements
6. Clean up excessive <hr/>

One-time script — idempotent (checks for existing ToC).
"""

import re
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

PAGE_ID = "165052419"

# Section numbering and emoji mapping
SECTION_MAP = {
    "⚠️ Scope Clarification — Per-Coupon vs Cross-Coupon": "1. ⚠️ Scope Clarification — Per-Coupon vs Cross-Coupon",
    "BEP-3331 Implementation Details (✅ Deployed)": "2. ✅ BEP-3331 Implementation Details (Deployed)",
    "Overview": "3. 🎯 Overview",
    "Scope": "4. 📐 Scope",
    "Technical Design": "5. 🔧 Technical Design",
    "NOT Changing": "6. 🚫 NOT Changing",
    "Test Plan": "7. 🧪 Test Plan",
    "Deployment Notes": "8. 🚀 Deployment Notes",
    "File Structure Reference": "9. 📁 File Structure Reference",
    "Related Documents": "10. 🔗 Related Documents",
    "Revision History": "11. 📝 Revision History",
}


def info_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="info" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def note_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def warning_panel(content: str) -> str:
    return (
        '<ac:structured-macro ac:name="warning" ac:schema-version="1">'
        f"<ac:rich-text-body>{content}</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


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
    print(f"  Version: {version}")

    # Idempotency check
    if 'ac:name="toc"' in content and "1. ⚠️" in content:
        print("  Already formatted — skipping")
        return

    changes = []

    # 1. Remove redundant H1 (it's the same as page title)
    # Handles both <p></p> and <p /> variants + &mdash; entities
    h1_pattern = r"<p\s*/?>(?:</p>)?\s*<h1>.*?</h1>\n?"
    if re.search(h1_pattern, content):
        content = re.sub(h1_pattern, "", content, count=1)
        changes.append("Removed redundant H1")

    # 2. Remove trailing empty <p></p> and <p />
    content = re.sub(r"<p\s*/?>\s*(?:</p>)?\s*$", "", content)
    content = re.sub(r"^<p\s*/?>\s*(?:</p>)?", "", content)
    changes.append("Removed empty paragraphs")

    # 3. Convert blockquotes to panels
    # First blockquote: metadata (Ticket, Epic, Status) → info panel
    meta_bq = re.search(
        r"<blockquote>\s*<p>(.*?Ticket:.*?Status:.*?)</p>\s*</blockquote>",
        content,
        re.DOTALL,
    )
    if meta_bq:
        inner = meta_bq.group(1)
        content = content.replace(
            meta_bq.group(0),
            info_panel(f"<p>{inner}</p>"),
        )
        changes.append("Converted metadata blockquote to info panel")

    # Implementation order blockquote → warning panel
    impl_bq = re.search(
        r"<blockquote>\s*<p>(<strong>Implementation Order:</strong>.*?)</p>\s*</blockquote>",
        content,
        re.DOTALL,
    )
    if impl_bq:
        inner = impl_bq.group(1)
        content = content.replace(
            impl_bq.group(0),
            warning_panel(f"<p>{inner}</p>"),
        )
        changes.append("Converted implementation order blockquote to warning panel")

    # Epic boundary blockquote → note panel
    epic_bq = re.search(
        r"<blockquote>\s*<p>(<strong>Epic Boundary:</strong>.*?)</p>\s*</blockquote>",
        content,
        re.DOTALL,
    )
    if epic_bq:
        inner = epic_bq.group(1)
        content = content.replace(
            epic_bq.group(0),
            note_panel(f"<p>{inner}</p>"),
        )
        changes.append("Converted epic boundary blockquote to note panel")

    # 4. Number sections with emoji
    # Handle both — and &mdash; variants
    for old_title, new_title in SECTION_MAP.items():
        # Try exact match first
        old_h2 = f"<h2>{old_title}</h2>"
        new_h2 = f"<h2>{new_title}</h2>"
        if old_h2 in content:
            content = content.replace(old_h2, new_h2)
            changes.append(f"Renamed: {old_title}")
        else:
            # Try with &mdash; entity
            old_h2_entity = f"<h2>{old_title.replace('—', '&mdash;')}</h2>"
            if old_h2_entity in content:
                content = content.replace(old_h2_entity, new_h2)
                changes.append(f"Renamed: {old_title}")

    # 5. Remove excessive <hr/> and <hr /> between sections
    content = re.sub(r"(<hr\s*/>\s*){2,}", "<hr />\n", content)

    # 6. Add ToC at top
    if 'ac:name="toc"' not in content:
        content = TOC_MACRO + content
        changes.append("Added Table of Contents")

    # Summary
    print(f"  Changes ({len(changes)}):")
    for c in changes:
        print(f"    - {c}")

    if dry_run:
        print("  DRY RUN — no changes applied")
        out = Path(__file__).parent.parent / "tasks" / "page-165052419-preview.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"  Preview saved to {out}")
        return

    # Note: update_page() internally does version+1
    api.update_page(
        page_id=PAGE_ID,
        title=title,
        content=content,
        version=version,
    )
    print(f"  ✅ Updated to version {version + 1}")


if __name__ == "__main__":
    main()
