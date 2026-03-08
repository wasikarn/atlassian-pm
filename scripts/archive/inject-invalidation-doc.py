#!/usr/bin/env python3
"""Add Data Invalidation Strategy section to Confluence page 165019651.

Fetches page storage format, inserts new section before
"Relationship to BEP-3302", and updates via REST API.

One-time script — idempotent (checks for existing section).
"""

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts"))
from lib.auth import create_ssl_context, get_auth_header, load_credentials

PAGE_ID = "165019651"

NEW_SECTION = """<hr />
<h2>Data Invalidation Strategy</h2>
<p>ทั้ง 4 tickets ใช้ Redis เป็น <strong>derived cache</strong> จาก DB — ต้องมีกลไกรักษาความสอดคล้องของข้อมูล:</p>

<table data-layout="default">
<colgroup><col style="width: 100px;" /><col style="width: 120px;" /><col style="width: 120px;" /><col style="width: 120px;" /><col style="width: 140px;" /></colgroup>
<thead>
<tr>
<th><p><strong>Ticket</strong></p></th>
<th><p><strong>TTL / Cleanup</strong></p></th>
<th><p><strong>Write Sync</strong></p></th>
<th><p><strong>Correction</strong></p></th>
<th><p><strong>Reconciliation</strong></p></th>
</tr>
</thead>
<tbody>
<tr>
<td><p>BEP-3314</p></td>
<td><p>✅ EXPIRE + ZREMRANGEBYSCORE (Lua atomic)</p></td>
<td><p>✅ Atomic Lua script — 1 round-trip</p></td>
<td><p>N/A (ephemeral)</p></td>
<td><p>N/A (self-cleaning)</p></td>
</tr>
<tr>
<td><p>BEP-3315</p></td>
<td><p>✅ TTL on sorted set key</p></td>
<td><p>✅ ZADD/ZREM on <strong>all</strong> status transitions (create, cancel, expired, error)</p></td>
<td><p>✅ AC4: ZREM ครบทุก non-active status</p></td>
<td><p>✅ AC5: Hourly reconciliation — ZCARD vs DB count</p></td>
</tr>
<tr>
<td><p>BEP-3316</p></td>
<td><p>✅ 90d TTL + auto-expire</p></td>
<td><p>✅ ZINCRBY on play event</p></td>
<td><p>✅ AC3: ZINCRBY negative on refund/adjustment</p></td>
<td><p>✅ AC4: Daily reconciliation (3 AM) — scores vs DB SUM</p></td>
</tr>
<tr>
<td><p>BEP-3317</p></td>
<td><p>✅ EXPIRE 90d (new — fixes memory leak)</p></td>
<td><p>✅ INCRBYFLOAT (existing)</p></td>
<td><p>N/A (accumulate-only)</p></td>
<td><p>N/A (TTL handles cleanup)</p></td>
</tr>
</tbody>
</table>

<h3>Common Patterns</h3>
<ul>
<li><strong>Fallback:</strong> ทุก read path ต้อง fallback ไป DB ถ้า Redis miss — backward compatible</li>
<li><strong>Write-through:</strong> Redis update ต้องเกิดหลัง DB write สำเร็จเท่านั้น (not before)</li>
<li><strong>Reconciliation:</strong> BEP-3315 (hourly) และ BEP-3316 (daily) มี background job ตรวจสอบ discrepancy</li>
<li><strong>No dual-write risk:</strong> ทั้ง 4 tickets ใช้ ioredis ตรง ไม่ผ่าน Bentocache — ลด failure mode</li>
</ul>
"""


def main():
    dry_run = "--dry-run" in sys.argv

    creds = load_credentials()
    base_url = creds["CONFLUENCE_URL"].rstrip("/")
    auth_header = get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"])
    ssl_ctx = create_ssl_context()

    # 1. Fetch current page
    url = f"{base_url}/rest/api/content/{PAGE_ID}?expand=body.storage,version"
    req = urllib.request.Request(url)
    req.add_header("Authorization", auth_header)
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
        page = json.loads(resp.read().decode("utf-8"))

    title = page["title"]
    version = page["version"]["number"]
    storage = page["body"]["storage"]["value"]

    print(f"Page: {title} (v{version})")

    # 2. Idempotency check
    if "Data Invalidation Strategy" in storage:
        print("Section already exists — skipping")
        return

    # 3. Find insertion point: before "Relationship to BEP-3302" heading
    marker = re.search(r"<h2>\s*Relationship to BEP-3302", storage)
    if not marker:
        print("ERROR: Could not find 'Relationship to BEP-3302' heading")
        sys.exit(1)

    # Insert before the <hr /> that precedes the heading
    insert_pos = marker.start()
    # Check if there's an <hr /> right before
    before = storage[:insert_pos].rstrip()
    if before.endswith("<hr />"):
        insert_pos = before.rfind("<hr />")

    updated = storage[:insert_pos] + NEW_SECTION + "\n" + storage[insert_pos:]

    if dry_run:
        print(f"DRY RUN — would insert {len(NEW_SECTION)} chars at position {insert_pos}")
        return

    # 4. Update page
    update_data = {
        "version": {"number": version + 1},
        "title": title,
        "type": "page",
        "body": {
            "storage": {
                "value": updated,
                "representation": "storage",
            }
        },
    }

    update_url = f"{base_url}/rest/api/content/{PAGE_ID}"
    update_req = urllib.request.Request(update_url, method="PUT")
    update_req.add_header("Authorization", auth_header)
    update_req.add_header("Content-Type", "application/json")
    update_req.data = json.dumps(update_data).encode("utf-8")

    try:
        with urllib.request.urlopen(update_req, context=ssl_ctx, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            new_version = result["version"]["number"]
            print(f"Updated successfully — v{version} → v{new_version}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"ERROR: HTTP {e.code} — {body[:300]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
