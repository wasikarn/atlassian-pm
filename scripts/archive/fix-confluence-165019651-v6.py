#!/usr/bin/env python3
"""Fix Confluence page 165019651 v6: replace broken mermaid-cloud with code block.

The Mermaid plugin on this Confluence instance is a Forge app
(com.atlassian.confluence.plugins.mermaid-diagrams-viewer).
It renders Mermaid diagrams from code blocks with language=mermaid.

Changes:
1. Replace broken ac:structured-macro mermaid-cloud with code block language=mermaid
2. Clean up <p></p> artifacts around code blocks

One-time script — idempotent.
"""

import re
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts")
)
from lib import ConfluenceAPI
from lib.auth import create_ssl_context, get_auth_header, load_credentials

PAGE_ID = "165019651"

MERMAID_CODE_BLOCK = """\
<ac:structured-macro ac:name="code" ac:schema-version="1">\
<ac:parameter ac:name="language">mermaid</ac:parameter>\
<ac:parameter ac:name="title">Implementation Priority Workflow</ac:parameter>\
<ac:plain-text-body><![CDATA[graph TD
    subgraph P1["P1 — Critical · 4 SP"]
        BEP3317["BEP-3317\\nCampaign Cost TTL + Lock\\n2 SP · Bug fix"]
        BEP3314["BEP-3314\\nRate Limiter Sliding Window\\n2 SP · Security"]
    end
    subgraph P2["P2 — Performance · 5 SP"]
        BEP3316["BEP-3316\\nRevenue Ranking ZINCRBY\\n2 SP · Report perf"]
        BEP3315["BEP-3315\\nPlaySchedule ZCOUNT\\n3 SP · N+1 queries"]
    end
    P1 --> P2]]>\
</ac:plain-text-body>\
</ac:structured-macro>"""


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

    print(f"=== Fixing {title} (v{version}) ===")

    changes = []

    # 1. Replace broken mermaid-cloud macro with code block
    mermaid_pattern = re.compile(
        r'<ac:structured-macro[^>]*ac:name="mermaid-cloud"[^>]*>.*?</ac:structured-macro>',
        re.DOTALL,
    )
    match = mermaid_pattern.search(content)
    if match:
        content = mermaid_pattern.sub(MERMAID_CODE_BLOCK, content)
        changes.append("Replaced mermaid-cloud macro with code block language=mermaid")
    else:
        # Check if already a mermaid code block
        if 'ac:name="language">mermaid' in content:
            print("  Mermaid code block already correct — skipping")
        else:
            print("  WARNING: No mermaid macro found")

    # 2. Clean up empty <p></p> artifacts
    before = len(content)
    content = content.replace("</ac:structured-macro><p></p>", "</ac:structured-macro>")
    content = content.replace("<p></p><h2>", "<h2>")
    # Remove trailing <p></p>
    if content.rstrip().endswith("<p></p>"):
        content = content.rstrip()
        content = content[: content.rfind("<p></p>")]
        changes.append("Removed trailing empty <p></p>")
    if len(content) < before:
        changes.append("Cleaned up empty <p></p> artifacts")

    if not changes:
        print("  No changes needed")
        return

    print(f"  Changes ({len(changes)}):")
    for c in changes:
        print(f"    - {c}")

    if dry_run:
        # Show mermaid section
        idx = content.find("language\">mermaid")
        if idx > 0:
            print(f"\n  Mermaid block preview:")
            print(f"  {content[max(0,idx-80):idx+200]}")
        print("\n  DRY RUN — not saving")
        return

    result = api.update_page(PAGE_ID, title, content, version)
    print(f"  Updated to v{result['version']['number']}")


if __name__ == "__main__":
    main()
