#!/usr/bin/env python3
"""Test: Mermaid edge animation on Confluence Forge plugin.

Tests 3 animation styles:
  1. animate: true (basic)
  2. animation: fast/slow (speed shortcuts)
  3. classDef with custom CSS animation

Usage:
  python3 scripts/test-mermaid-animation.py --dry-run    # preview HTML
  python3 scripts/test-mermaid-animation.py               # create test page
  python3 scripts/test-mermaid-animation.py --cleanup      # delete test page
"""

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts")
)
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib import ConfluenceAPI

SPACE_KEY = "BEP"
PARENT_PAGE_ID = "165019751"  # Architecture proposal parent
TEST_PAGE_TITLE = "TEST: Mermaid Animation Support (delete me)"

# ─── Mermaid Forge App Constants ───
MERMAID_APP_ID = "23392b90-4271-4239-98ca-a3e96c663cbb"
MERMAID_ENV_ID = "63d4d207-ac2f-4273-865c-0240d37f044a"
MERMAID_INSTALL_ID = "5c245bad-32e8-4c74-aa1c-6d227f18fa22"
CLOUD_ID = "85ad5bd2-ef9c-477e-b000-062f1421d0c0"
RESOURCE_UPLOAD_ID = "9f9d6c69-f97f-4e32-b336-cca6d907aa0b"
ACCOUNT_ID = "712020:64219948-720a-4925-a48c-d7a53557993c"
BEP_SPACE_ID = "1081347"
WORKSPACE_ID = "2f960cad-efff-4621-bb36-aa7f65cf74df"
ICON_URL = (
    f"https://icon.cdn.prod.atlassian-dev.net/"
    f"{MERMAID_APP_ID}/{MERMAID_ENV_ID}/{RESOURCE_UPLOAD_ID}/icons/app-icon.png"
)

# Global code block counter
_code_block_count = 0


def mermaid_diagram(code: str, page_id: str) -> str:
    """Generate Mermaid code block + Forge renderer macro."""
    global _code_block_count
    index = _code_block_count
    _code_block_count += 1

    local_id = str(uuid.uuid4())
    code_local_id = str(uuid.uuid4())
    ext_id = (
        f"ari:cloud:ecosystem::extension/"
        f"{MERMAID_APP_ID}/{MERMAID_ENV_ID}/static/mermaid-diagram"
    )
    ext_key = f"{MERMAID_APP_ID}/{MERMAID_ENV_ID}/static/mermaid-diagram"
    consent_url = (
        f"https://id.atlassian.com/outboundAuth/start?"
        f"containerId={MERMAID_APP_ID}_{MERMAID_ENV_ID}"
        f"&amp;serviceKey=atlassian-token-service-key"
        f"&amp;cloudId={CLOUD_ID}"
        f"&amp;isAccountBased=true"
        f"&amp;scopes=read%3Apage%3Aconfluence+offline_access"
    )
    context_ari = f"ari:cloud:confluence:{CLOUD_ID}:workspace/{WORKSPACE_ID}"

    params = (
        f'<ac:adf-parameter key="local-id">{local_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-id">{ext_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-title">Mermaid diagram</ac:adf-parameter>'
        f'<ac:adf-parameter key="layout">extension</ac:adf-parameter>'
        f'<ac:adf-parameter key="forge-environment">PRODUCTION</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-properties">'
        f'<ac:adf-parameter key="extension">'
        f'<ac:adf-parameter key="id">{ext_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="app-id">{MERMAID_APP_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="key">mermaid-diagram</ac:adf-parameter>'
        f'<ac:adf-parameter key="environment-id">{MERMAID_ENV_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="environment-type">PRODUCTION</ac:adf-parameter>'
        f'<ac:adf-parameter key="environment-key">production</ac:adf-parameter>'
        f'<ac:adf-parameter key="properties">'
        f'<ac:adf-parameter key="resource-upload-id">{RESOURCE_UPLOAD_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="resource">custom-ui</ac:adf-parameter>'
        f'<ac:adf-parameter key="icon">{ICON_URL}</ac:adf-parameter>'
        f'<ac:adf-parameter key="description">Render a Mermaid diagram from a code block on a page</ac:adf-parameter>'
        f'<ac:adf-parameter key="categories">'
        f'<ac:adf-parameter-value>confluence-content</ac:adf-parameter-value>'
        f'<ac:adf-parameter-value>development</ac:adf-parameter-value>'
        f'<ac:adf-parameter-value>formatting</ac:adf-parameter-value>'
        f'<ac:adf-parameter-value>visuals</ac:adf-parameter-value>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="title">Mermaid diagram</ac:adf-parameter>'
        f'<ac:adf-parameter key="type">xen:macro</ac:adf-parameter>'
        f'<ac:adf-parameter key="config">'
        f'<ac:adf-parameter key="render">native</ac:adf-parameter>'
        f'<ac:adf-parameter key="resource">macro-config</ac:adf-parameter>'
        f'<ac:adf-parameter key="title">Mermaid diagram configuration</ac:adf-parameter>'
        f'<ac:adf-parameter key="viewport-size">small</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="key">mermaid-diagram</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="type">xen:macro</ac:adf-parameter>'
        f'<ac:adf-parameter key="installation-id">{MERMAID_INSTALL_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="app-version">2.45.0</ac:adf-parameter>'
        f'<ac:adf-parameter key="consent-url">{consent_url}</ac:adf-parameter>'
        f'<ac:adf-parameter key="egress"><ac:adf-parameter-value></ac:adf-parameter-value></ac:adf-parameter>'
        f'<ac:adf-parameter key="scopes"><ac:adf-parameter-value>read:page:confluence</ac:adf-parameter-value></ac:adf-parameter>'
        f'<ac:adf-parameter key="data-classification-policy-decision">'
        f'<ac:adf-parameter key="status">ALLOWED</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="extension-data">'
        f'<ac:adf-parameter key="type">macro</ac:adf-parameter>'
        f'<ac:adf-parameter key="content">'
        f'<ac:adf-parameter key="id">{page_id}</ac:adf-parameter>'
        f'<ac:adf-parameter key="type">page</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="space">'
        f'<ac:adf-parameter key="key">BEP</ac:adf-parameter>'
        f'<ac:adf-parameter key="id">{BEP_SPACE_ID}</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="account-id">{ACCOUNT_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="cloud-id">{CLOUD_ID}</ac:adf-parameter>'
        f'<ac:adf-parameter key="context-ids">'
        f'<ac:adf-parameter-value>{context_ari}</ac:adf-parameter-value>'
        f'</ac:adf-parameter>'
        f'</ac:adf-parameter>'
        f'<ac:adf-parameter key="guest-params">'
        f'<ac:adf-parameter key="index" type="integer">{index}</ac:adf-parameter>'
        f'</ac:adf-parameter>'
    )

    def adf_node():
        return (
            f'<ac:adf-node type="extension">'
            f'<ac:adf-attribute key="extension-key">{ext_key}</ac:adf-attribute>'
            f'<ac:adf-attribute key="extension-type">com.atlassian.ecosystem</ac:adf-attribute>'
            f'<ac:adf-attribute key="parameters">{params}</ac:adf-attribute>'
            f'<ac:adf-attribute key="text">Mermaid diagram</ac:adf-attribute>'
            f'<ac:adf-attribute key="layout">default</ac:adf-attribute>'
            f'<ac:adf-attribute key="local-id">{local_id}</ac:adf-attribute>'
            f'</ac:adf-node>'
        )

    code_html = (
        f'<ac:structured-macro ac:local-id="{code_local_id}" '
        f'ac:name="code" ac:schema-version="1">'
        f'<ac:parameter ac:name="breakoutMode">wide</ac:parameter>'
        f'<ac:parameter ac:name="breakoutWidth">760</ac:parameter>'
        f'<ac:parameter ac:name="language">mermaid</ac:parameter>'
        f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )

    forge_html = (
        f'<ac:adf-extension>'
        f'{adf_node()}'
        f'<ac:adf-fallback>{adf_node()}</ac:adf-fallback>'
        f'</ac:adf-extension>'
    )

    return code_html + forge_html


# ─── Test Diagrams ───

# Test 1: animate: true (basic)
DIAGRAM_1_BASIC = """\
flowchart LR
    A[Start] e1@--> B[Process]
    B e2@--> C[End]
    e1@{ animate: true }
    e2@{ animate: true }"""

# Test 2: animation speed (fast/slow)
DIAGRAM_2_SPEED = """\
flowchart LR
    A[Start] e1@--> B[Fast]
    B e2@--> C[Slow]
    C e3@--> D[End]
    e1@{ animation: fast }
    e2@{ animation: slow }
    e3@{ animate: true }"""

# Test 3: classDef custom CSS animation
DIAGRAM_3_CLASSDEF = """\
flowchart LR
    A[Source] e1@==> B[Pipeline]
    B e2@==> C[Destination]
    classDef animateEdge stroke-dasharray: 9\\,5,stroke-dashoffset: 900,animation: dash 25s linear infinite;
    class e1 animateEdge
    class e2 animateEdge"""

# Test 4: Mixed — some animated, some static
DIAGRAM_4_MIXED = """\
flowchart TD
    A[Cron] --> B[Calculate]
    B e1@--> C[Push to Player]
    C e2@--> D[Player Receives]
    D --> E[Play Ad]
    e1@{ animation: fast }
    e2@{ animation: slow }
    style C fill:#ffd700,stroke:#333
    style D fill:#ffd700,stroke:#333"""


def build_test_page(page_id: str) -> str:
    """Build test page content with 4 animation test diagrams."""
    global _code_block_count
    _code_block_count = 0

    sections = []

    sections.append("<h1>Mermaid Animation Test</h1>")
    sections.append(
        "<p>Testing Mermaid edge animation support on Confluence Forge plugin (v11.12.2).</p>"
    )
    sections.append("<p>Each diagram tests a different animation syntax.</p>")

    # Test 1
    sections.append("<h2>Test 1: animate: true (basic)</h2>")
    sections.append(
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        "<ac:rich-text-body><p>Syntax: <code>e1@{ animate: true }</code></p>"
        "<p><strong>Expected:</strong> Dashed edges with animation (marching ants)</p>"
        "</ac:rich-text-body></ac:structured-macro>"
    )
    sections.append(mermaid_diagram(DIAGRAM_1_BASIC, page_id=page_id))

    # Test 2
    sections.append("<h2>Test 2: animation speed (fast/slow)</h2>")
    sections.append(
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        "<ac:rich-text-body><p>Syntax: <code>e1@{ animation: fast }</code> / <code>e2@{ animation: slow }</code></p>"
        "<p><strong>Expected:</strong> Different animation speeds on each edge</p>"
        "</ac:rich-text-body></ac:structured-macro>"
    )
    sections.append(mermaid_diagram(DIAGRAM_2_SPEED, page_id=page_id))

    # Test 3
    sections.append("<h2>Test 3: classDef custom CSS</h2>")
    sections.append(
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        "<ac:rich-text-body><p>Syntax: <code>classDef animateEdge stroke-dasharray: 9\\,5, ...</code></p>"
        "<p><strong>Expected:</strong> Custom CSS animation on thick edges</p>"
        "</ac:rich-text-body></ac:structured-macro>"
    )
    sections.append(mermaid_diagram(DIAGRAM_3_CLASSDEF, page_id=page_id))

    # Test 4
    sections.append("<h2>Test 4: Mixed (animated + static)</h2>")
    sections.append(
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        "<ac:rich-text-body><p>Some edges animated, some static. Node styles combined.</p>"
        "<p><strong>Expected:</strong> Only middle edges animated, others static</p>"
        "</ac:rich-text-body></ac:structured-macro>"
    )
    sections.append(mermaid_diagram(DIAGRAM_4_MIXED, page_id=page_id))

    # Summary
    sections.append("<h2>Results</h2>")
    sections.append(
        "<table><tbody>"
        "<tr><th>Test</th><th>Syntax</th><th>Result</th></tr>"
        "<tr><td>1. Basic</td><td><code>animate: true</code></td><td>(check visually)</td></tr>"
        "<tr><td>2. Speed</td><td><code>animation: fast/slow</code></td><td>(check visually)</td></tr>"
        "<tr><td>3. classDef</td><td><code>classDef + class</code></td><td>(check visually)</td></tr>"
        "<tr><td>4. Mixed</td><td>animated + static</td><td>(check visually)</td></tr>"
        "</tbody></table>"
    )

    sections.append(
        "<p><em>Created by test-mermaid-animation.py — safe to delete this page after testing.</em></p>"
    )

    return "\n".join(sections)


def main():
    dry_run = "--dry-run" in sys.argv
    page_id_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--page-id="):
            page_id_arg = arg.split("=", 1)[1]

    creds = load_credentials()
    api = ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(
            creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]
        ),
        ssl_context=create_ssl_context(),
    )

    if page_id_arg:
        # Update existing page
        page = api.get_page(page_id_arg)
        version = page["version"]["number"]
        print(f"=== Updating test page: {page_id_arg} (v{version}) ===")
        content = build_test_page(page_id_arg)
        print(f"  Content: {len(content):,} chars, {_code_block_count} code blocks")

        if dry_run:
            out = Path(__file__).parent.parent / "tasks" / "mermaid-animation-test.html"
            out.parent.mkdir(exist_ok=True)
            out.write_text(content, encoding="utf-8")
            print(f"  DRY RUN — preview: {out}")
            return

        api.update_page(
            page_id=page_id_arg,
            title=TEST_PAGE_TITLE,
            content=content,
            version=version,
        )
        print(f"  Updated to v{version + 1}")
        url = f"https://100-stars.atlassian.net/wiki/spaces/{SPACE_KEY}/pages/{page_id_arg}"
        print(f"  URL: {url}")
        return

    # Create new page
    print("=== Creating test page ===")
    # First create with placeholder (need page_id for Forge macros)
    result = api.create_page(
        space_key=SPACE_KEY,
        title=TEST_PAGE_TITLE,
        content="<p>Loading animation test...</p>",
        parent_id=PARENT_PAGE_ID,
    )
    page_id = result.get("id", "unknown")
    print(f"  Created placeholder: {page_id}")

    # Now rebuild with correct page_id
    content = build_test_page(page_id)
    print(f"  Content: {len(content):,} chars, {_code_block_count} code blocks")

    if dry_run:
        out = Path(__file__).parent.parent / "tasks" / "mermaid-animation-test.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"  DRY RUN — preview: {out}")
        print(f"  NOTE: Page {page_id} created as placeholder — delete manually if needed")
        return

    page = api.get_page(page_id)
    api.update_page(
        page_id=page_id,
        title=TEST_PAGE_TITLE,
        content=content,
        version=page["version"]["number"],
    )
    print(f"  Updated with animation diagrams")

    url = f"https://100-stars.atlassian.net/wiki/spaces/{SPACE_KEY}/pages/{page_id}"
    print(f"  URL: {url}")
    print(f"\n  To delete: go to page → ⋯ → Delete")


if __name__ == "__main__":
    main()
