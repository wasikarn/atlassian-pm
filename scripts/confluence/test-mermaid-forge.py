#!/usr/bin/env python3
"""Test: Programmatic Mermaid Forge macro on Confluence.

Proof-of-concept: Replace the Player State Machine ASCII diagram (Section 5)
with a rendered Mermaid stateDiagram-v2.

Usage:
  python3 scripts/test-mermaid-forge.py --dry-run    # preview HTML
  python3 scripts/test-mermaid-forge.py               # update page
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts")
)
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib import ConfluenceAPI

PAGE_ID = "165019751"

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


def mermaid_block(code: str, index: int, page_id: str = PAGE_ID) -> str:
    """Generate Mermaid code block + Forge renderer macro.

    Args:
        code: Mermaid diagram source text
        index: 0-based index of this mermaid block on the page
        page_id: Confluence page ID
    """
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

    # ── Shared parameters block (used in both main node and fallback) ──
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

    # ── adf-node block (shared between main and fallback) ──
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

    # ── Code block (mermaid source) ──
    code_html = (
        f'<ac:structured-macro ac:local-id="{code_local_id}" '
        f'ac:name="code" ac:schema-version="1">'
        f'<ac:parameter ac:name="breakoutMode">wide</ac:parameter>'
        f'<ac:parameter ac:name="breakoutWidth">760</ac:parameter>'
        f'<ac:parameter ac:name="language">mermaid</ac:parameter>'
        f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )

    # ── Forge extension (renderer) ──
    forge_html = (
        f'<ac:adf-extension>'
        f'{adf_node()}'
        f'<ac:adf-fallback>{adf_node()}</ac:adf-fallback>'
        f'</ac:adf-extension>'
    )

    return code_html + forge_html


# ─── Test: Player State Machine as Mermaid ───
STATE_MACHINE_MERMAID = (
    "stateDiagram-v2\n"
    "    [*] --> BOOT\n"
    "\n"
    "    BOOT --> SPLASH : No localStorage\n"
    "    BOOT --> CACHED_PLAYBACK : Has localStorage\n"
    "\n"
    "    SPLASH --> SYNCING_FIRST : Connected\n"
    "    SPLASH --> SPLASH : No internet (retry 5s)\n"
    "\n"
    "    CACHED_PLAYBACK --> OFFLINE_PLAYBACK : Not online\n"
    "    CACHED_PLAYBACK --> SYNCING_DELTA : Online\n"
    "\n"
    "    SYNCING_FIRST --> ONLINE_PLAYBACK : Playlist fetched\n"
    "    SYNCING_DELTA --> ONLINE_PLAYBACK : Delta applied\n"
    "\n"
    "    ONLINE_PLAYBACK --> OFFLINE_PLAYBACK : Network drop\n"
    "\n"
    "    OFFLINE_PLAYBACK --> ONLINE_PLAYBACK : Reconnect + sync\n"
    "    OFFLINE_PLAYBACK --> FALLBACK : Tier 1+2 exhausted\n"
    "\n"
    "    FALLBACK --> ONLINE_PLAYBACK : Reconnect + sync\n"
    "    FALLBACK --> SPLASH_LAST : Tier 3 empty\n"
    "\n"
    "    note right of CACHED_PLAYBACK : Play from cache immediately\n"
    "    note right of OFFLINE_PLAYBACK : Tier 1 then 2 then 3\n"
    "    note right of SPLASH_LAST : Logo + contact admin"
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

    print(f"=== Test Mermaid Forge Macro ===")
    print(f"  Page: {title} (v{version})")

    # Find the existing State Machine code block (mermaid from v4, or text from v3)
    import re

    # String-based approach (regex was too greedy across multiple code blocks)
    # Step 1: Find the mermaid language parameter
    mermaid_marker = '<ac:parameter ac:name="language">mermaid</ac:parameter>'
    marker_pos = content.find(mermaid_marker)

    if marker_pos == -1:
        # Fallback: look for original text code block with "Player State Machine" title
        marker_pos = content.find('Player State Machine</ac:parameter>')
        if marker_pos == -1:
            print("  ERROR: Could not find State Machine block (neither mermaid nor text)")
            sys.exit(1)

    # Step 2: Find enclosing <ac:structured-macro> boundaries
    macro_open = '<ac:structured-macro'
    macro_close = '</ac:structured-macro>'
    macro_start = content.rfind(macro_open, 0, marker_pos)
    macro_end = content.find(macro_close, marker_pos) + len(macro_close)

    print(f"  Found code block at position {macro_start}-{macro_end} ({macro_end - macro_start:,} chars)")

    # Step 3: Check if Forge ac:adf-extension follows immediately
    ext_open = '<ac:adf-extension>'
    ext_close = '</ac:adf-extension>'
    rest = content[macro_end:macro_end + 50000]  # look ahead up to 50K
    if rest.lstrip().startswith(ext_open):
        ext_start = content.find(ext_open, macro_end)
        ext_end = content.find(ext_close, ext_start) + len(ext_close)
        total_end = ext_end
        print(f"  Found Forge extension at {ext_start}-{ext_end} ({ext_end - ext_start:,} chars)")
    else:
        total_end = macro_end
        print("  No Forge extension found after code block")

    match_start = macro_start
    match_end = total_end
    print(f"  Total match: {match_start}-{match_end} ({match_end - match_start:,} chars)")

    # Count ALL code blocks before this position (Forge index counts all code blocks, not just mermaid)
    all_code_blocks_before = len(re.findall(
        r'<ac:structured-macro[^>]*ac:name="code"',
        content[:match_start]
    ))
    print(f"  Code blocks before this position: {all_code_blocks_before}")

    # Generate replacement
    replacement = mermaid_block(STATE_MACHINE_MERMAID, index=all_code_blocks_before, page_id=PAGE_ID)

    new_content = content[:match_start] + replacement + content[match_end:]

    print(f"  Original size: {len(content):,} chars")
    print(f"  New size: {len(new_content):,} chars")
    print(f"  Delta: {len(new_content) - len(content):+,} chars")

    if dry_run:
        print("  DRY RUN — no changes applied")
        out = Path(__file__).parent.parent / "tasks" / "mermaid-test-preview.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(new_content, encoding="utf-8")
        print(f"  Preview: {out}")

        # Also save just the mermaid block for inspection
        out2 = Path(__file__).parent.parent / "tasks" / "mermaid-block-sample.html"
        out2.write_text(replacement, encoding="utf-8")
        print(f"  Sample block: {out2}")
        return

    api.update_page(
        page_id=PAGE_ID,
        title=title,
        content=new_content,
        version=version,
    )
    print(f"  Updated to v{version + 1}")


if __name__ == "__main__":
    main()
