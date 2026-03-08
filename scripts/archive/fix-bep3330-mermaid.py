#!/usr/bin/env python3
"""Replace ASCII Flow Diagram with Mermaid diagram on BEP-3330 tech note page."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/atlassian-scripts"))

from lib import ConfluenceAPI, create_ssl_context, get_auth_header, load_credentials

PAGE_ID = "165052419"

MERMAID_BLOCK = """\
<ac:structured-macro ac:name="code" ac:schema-version="1">\
<ac:parameter ac:name="language">mermaid</ac:parameter>\
<ac:parameter ac:name="title">useCoupon Validation Flow</ac:parameter>\
<ac:plain-text-body><![CDATA[flowchart TD
    A["🔷 useCoupon Request"] --> B["validateCoupon()"]
    B --> C["Check status, dates, stock"]
    C --> D["checkCouponMaxPerUser()"]
    C --> E["checkCouponMaxPerUserPerDay()"]

    D --> D1["count ALL redemptions"]
    D1 --> D2{"count < maxPerUser?"}
    D2 -- "Yes" --> PASS1["✅ Pass"]
    D2 -- "No" --> FAIL1["❌ Reject: lifetime limit"]

    E --> E1["count TODAY's redemptions\n(WHERE created_at BETWEEN dayStart AND dayEnd)"]
    E1 --> E2{"count < maxPerUserPerDay?"}
    E2 -- "Yes" --> PASS2["✅ Pass"]
    E2 -- "No" --> FAIL2["❌ Reject: daily limit"]

    PASS1 --> F["🟢 Proceed to redeem"]
    PASS2 --> F

    style A fill:#4C9AFF,color:#fff
    style F fill:#36B37E,color:#fff
    style FAIL1 fill:#FF5630,color:#fff
    style FAIL2 fill:#FF5630,color:#fff]]>\
</ac:plain-text-body>\
</ac:structured-macro>"""


def main():
    dry_run = "--dry-run" in sys.argv

    creds = load_credentials()
    api = ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    page = api.get_page(PAGE_ID)
    content = page["body"]["storage"]["value"]
    version = page["version"]["number"]
    print(f"Page: {page['title']} (v{version})")

    # Find the code block containing "useCoupon Request"
    pattern = re.compile(
        r'<ac:structured-macro ac:name="code"[^>]*>.*?useCoupon Request.*?</ac:structured-macro>',
        re.DOTALL,
    )

    match = pattern.search(content)
    if not match:
        print("❌ Could not find Flow Diagram code block")
        return 1

    print(f"Found Flow Diagram code block ({len(match.group())} chars)")

    new_content = content[: match.start()] + MERMAID_BLOCK + content[match.end() :]

    if dry_run:
        print("🔍 DRY RUN — no changes applied")
        return 0

    result = api.update_page(PAGE_ID, page["title"], new_content, version)
    print(f"✅ Replaced with Mermaid diagram, updated to v{result['version']['number']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
