#!/usr/bin/env python3
"""Update Confluence page 165019651 v5: add Mermaid workflow + clean up code blocks.

Changes:
1. Add Mermaid diagram for Implementation Priority workflow
2. Clean up empty <p></p> artifacts around code blocks
3. Remove stray newlines inside <p> tags before code macros

One-time script — idempotent (checks for existing mermaid macro).
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

MERMAID_DIAGRAM = """\
<ac:structured-macro ac:name="mermaid-cloud" ac:schema-version="1">\
<ac:plain-text-body><![CDATA[graph TD
    subgraph P1["P1 — Critical · 4 SP"]
        BEP3317["BEP-3317<br/>Campaign Cost TTL + Lock<br/>2 SP · Bug fix"]
        BEP3314["BEP-3314<br/>Rate Limiter Sliding Window<br/>2 SP · Security"]
    end
    subgraph P2["P2 — Performance · 5 SP"]
        BEP3316["BEP-3316<br/>Revenue Ranking ZINCRBY<br/>2 SP · Report perf"]
        BEP3315["BEP-3315<br/>PlaySchedule ZCOUNT<br/>3 SP · N+1 queries"]
    end
    P1 --> P2]]></ac:plain-text-body>\
</ac:structured-macro>"""

# Implementation Priority table to replace (keep as fallback text below diagram)
PRIORITY_TABLE_START = "<table>\n<thead>\n<tr>\n<th>Priority</th>"
PRIORITY_TABLE_END = "</tbody>\n</table>"


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

    print(f"=== Updating {title} (v{version}) ===")

    # Idempotency
    if "mermaid-cloud" in content:
        print("  Mermaid diagram already present — skipping")
        return

    changes = []

    # 1. Clean up empty <p></p> after code macros
    before_len = len(content)
    content = content.replace("</ac:structured-macro><p></p>", "</ac:structured-macro>")
    if len(content) < before_len:
        changes.append("Removed empty <p></p> after code macros")

    # 2. Clean up <p></p> before headings
    content = content.replace("<p></p><h2>", "<h2>")
    if len(content) < before_len:
        changes.append("Removed empty <p></p> before headings")

    # 3. Clean trailing newline inside <p> before code macro
    # Pattern: <p><strong>Before:</strong>\n</p><ac:structured-macro
    content = re.sub(
        r"</strong>\n</p><ac:structured-macro",
        "</strong></p>\n<ac:structured-macro",
        content,
    )
    changes.append("Fixed newlines inside <p> tags before code macros")

    # 4. Add Mermaid diagram after Implementation Priority heading
    impl_heading = "<h2>Implementation Priority</h2>"
    if impl_heading in content:
        # Find the priority table
        table_start_idx = content.find(PRIORITY_TABLE_START)
        table_end_idx = content.find(PRIORITY_TABLE_END, table_start_idx)

        if table_start_idx > 0 and table_end_idx > 0:
            table_end_idx += len(PRIORITY_TABLE_END)
            old_table = content[table_start_idx:table_end_idx]

            # Replace table with Mermaid + collapsed table
            replacement = (
                MERMAID_DIAGRAM
                + "\n"
                + '<ac:structured-macro ac:name="expand" ac:schema-version="1">'
                + '<ac:parameter ac:name="title">Priority Table (text fallback)</ac:parameter>'
                + "<ac:rich-text-body>"
                + old_table
                + "</ac:rich-text-body>"
                + "</ac:structured-macro>"
            )
            content = content[:table_start_idx] + replacement + content[table_end_idx:]
            changes.append(
                "Added Mermaid diagram + moved priority table to expand macro"
            )

    # 5. Remove trailing empty <p></p> at end
    if content.rstrip().endswith("<p></p>"):
        content = content.rstrip()
        content = content[: content.rfind("<p></p>")]
        changes.append("Removed trailing empty <p></p>")

    if not changes:
        print("  No changes needed")
        return

    print(f"  Changes ({len(changes)}):")
    for c in changes:
        print(f"    - {c}")

    if dry_run:
        print("  DRY RUN — not saving")
        return

    result = api.update_page(PAGE_ID, title, content, version)
    print(f"  Updated to v{result['version']['number']}")


if __name__ == "__main__":
    main()
