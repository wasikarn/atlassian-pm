#!/usr/bin/env python3
"""Inject data invalidation AC panels into BEP-3315 and BEP-3316.

Fetches current ADF description, finds the Reference section (last heading),
inserts new AC panels before it, and updates via REST API.

One-time script — safe to re-run (checks for existing panel text).
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

# Add atlassian-scripts lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts"))
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url


def make_panel(panel_type: str, lines: list[dict]) -> dict:
    """Build an ADF panel node."""
    return {
        "type": "panel",
        "content": [make_paragraph(line) for line in lines],
        "attrs": {"panelType": panel_type},
    }


def make_paragraph(parts: list[dict] | dict) -> dict:
    """Build an ADF paragraph from text parts."""
    if isinstance(parts, dict):
        parts = [parts]
    return {"type": "paragraph", "content": parts}


def bold(text: str) -> dict:
    return {"type": "text", "text": text, "marks": [{"type": "strong"}]}


def plain(text: str) -> dict:
    return {"type": "text", "text": text}


def code(text: str) -> dict:
    return {"type": "text", "text": text, "marks": [{"type": "code"}]}


def rule() -> dict:
    return {"type": "rule"}


# --- New panels for BEP-3315 ---
BEP_3315_NEW_PANELS = [
    make_panel("success", [
        [bold("AC4: Status Transition → ZREM ครบทุก non-active status")],
        [bold("Given: "), plain("PlaySchedule ถูก transition ออกจาก active pool ("), code("cancelled"), plain(", "), code("expired"), plain(", "), code("error"), plain(")")],
        [bold("When: "), plain("Status update สำเร็จใน DB")],
        [bold("Then: "), code("ZREM"), plain(" ลบออกจาก sorted set ทันที — ไม่เฉพาะ cancel แต่ครอบคลุมทุก non-active transition")],
    ]),
    make_panel("warning", [
        [bold("AC5: DB-Redis Consistency — Reconciliation")],
        [bold("Given: "), plain("Redis write อาจ fail (network timeout, Redis restart)")],
        [bold("When: "), plain("Periodic reconciliation job รัน (แนะนำทุก 1 ชั่วโมง)")],
        [bold("Then: "), plain("เปรียบเทียบ "), code("ZCARD"), plain(" กับ DB count query — ถ้า discrepancy > threshold → rebuild sorted set จาก DB + log alert")],
    ]),
]

# --- New panels for BEP-3316 ---
BEP_3316_NEW_PANELS = [
    make_panel("success", [
        [bold("AC3: Revenue Correction — Refund/Adjustment")],
        [bold("Given: "), plain("Revenue record ถูก refund หรือ adjust ย้อนหลัง")],
        [bold("When: "), plain("Financial adjustment บันทึกลง DB สำเร็จ")],
        [bold("Then: "), code("ZINCRBY"), plain(" ด้วยค่าลบ (negative amount) ใน daily sorted set — ถ้า adjustment เกิดข้ามวัน ให้ลดจาก key ของวันที่เกิด revenue เดิม")],
    ]),
    make_panel("warning", [
        [bold("AC4: DB-Redis Consistency — Daily Reconciliation")],
        [bold("Given: "), plain("Redis write อาจ fail หรือ data drift สะสม")],
        [bold("When: "), plain("Daily reconciliation job รัน (แนะนำตอนตี 3)")],
        [bold("Then: "), plain("เปรียบเทียบ sorted set scores กับ DB "), code("SUM(revenue) GROUP BY billboard_code"), plain(" — ถ้า diff > 1 บาท → rebuild key ของวันนั้น + log alert")],
    ]),
]

# --- Also update BEP-3315 scope table: add status-change row ---
BEP_3315_SCOPE_ROW = {
    "type": "tableRow",
    "content": [
        {"type": "tableCell", "attrs": {}, "content": [
            make_paragraph([code("app/Services/PlaySchedulePeriodService.ts")])
        ]},
        {"type": "tableCell", "attrs": {}, "content": [
            make_paragraph([plain("เพิ่ม ZREM เมื่อ status transition ไป non-active (cancelled/expired/error)")])
        ]},
    ],
}

# --- Also update BEP-3316 scope table: add refund row ---
BEP_3316_SCOPE_ROW = {
    "type": "tableRow",
    "content": [
        {"type": "tableCell", "attrs": {}, "content": [
            make_paragraph([code("app/Jobs/PlayHistoryRevenueDistribution.ts")])
        ]},
        {"type": "tableCell", "attrs": {}, "content": [
            make_paragraph([plain("เพิ่ม ZINCRBY negative เมื่อ refund/adjustment")])
        ]},
    ],
}


def find_reference_section_index(content: list) -> int:
    """Find the index of the Reference heading (section 6)."""
    for i, node in enumerate(content):
        if node.get("type") == "heading":
            text_content = node.get("content", [])
            for t in text_content:
                if t.get("type") == "text" and "Reference" in t.get("text", ""):
                    return i
    return -1


def find_scope_table_index(content: list) -> int:
    """Find the index of the Scope section's table."""
    in_scope = False
    for i, node in enumerate(content):
        if node.get("type") == "heading":
            text_content = node.get("content", [])
            for t in text_content:
                if t.get("type") == "text" and "Scope" in t.get("text", ""):
                    in_scope = True
                    break
            if not in_scope:
                continue
        if in_scope and node.get("type") == "table":
            return i
    return -1


def has_text_in_description(content: list, search_text: str) -> bool:
    """Check if text already exists in description (idempotency check)."""
    for node in content:
        if json.dumps(node).find(search_text) != -1:
            return True
    return False


def inject_panels(issue_key: str, api: JiraAPI, new_panels: list, scope_row: dict | None = None, dry_run: bool = False) -> bool:
    """Inject new panels before the Reference section."""
    issue = api.get_issue(issue_key)
    desc = issue["fields"].get("description")
    if not desc:
        print(f"  {issue_key}: No description found")
        return False

    content = deepcopy(desc.get("content", []))

    # Idempotency check
    check_text = "Reconciliation" if any("Reconciliation" in json.dumps(p) for p in new_panels) else "AC4"
    if has_text_in_description(content, check_text):
        print(f"  {issue_key}: Already has invalidation ACs — skipping")
        return False

    # Find Reference section
    ref_idx = find_reference_section_index(content)
    if ref_idx == -1:
        print(f"  {issue_key}: Reference section not found — appending at end")
        ref_idx = len(content)

    # Insert rule + panels before Reference
    insert_nodes = []
    for panel in new_panels:
        insert_nodes.append(panel)
    insert_nodes.append(rule())

    # Insert before the rule that precedes Reference (if exists)
    insert_at = ref_idx
    if insert_at > 0 and content[insert_at - 1].get("type") == "rule":
        insert_at = insert_at - 1  # replace the existing rule before Reference

    for i, node in enumerate(insert_nodes):
        content.insert(insert_at + i, node)

    # Add scope row if provided
    if scope_row:
        # Need to re-find scope table after insertion shifted indices
        scope_idx = find_scope_table_index(content)
        if scope_idx != -1:
            table = content[scope_idx]
            table_content = table.get("content", [])
            table_content.append(scope_row)
            print(f"  {issue_key}: Added scope table row")

    updated_desc = {"type": "doc", "version": 1, "content": content}

    if dry_run:
        print(f"  {issue_key}: DRY RUN — would add {len(new_panels)} panels")
        return True

    status = api.update_description(issue_key, updated_desc)
    if status in (200, 204):
        print(f"  {issue_key}: Updated successfully — added {len(new_panels)} panels")
        return True
    else:
        print(f"  {issue_key}: Update failed (HTTP {status})")
        return False


def main():
    dry_run = "--dry-run" in sys.argv

    creds = load_credentials()
    api = JiraAPI(
        base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    print("=== Injecting Data Invalidation ACs ===")
    if dry_run:
        print("(DRY RUN mode)")
    print()

    print("BEP-3315 (PlaySchedule Frequency Count):")
    r1 = inject_panels("BEP-3315", api, BEP_3315_NEW_PANELS, BEP_3315_SCOPE_ROW, dry_run)

    print()
    print("BEP-3316 (Billboard Revenue Ranking):")
    r2 = inject_panels("BEP-3316", api, BEP_3316_NEW_PANELS, BEP_3316_SCOPE_ROW, dry_run)

    print()
    if r1 or r2:
        print("Done. Run cache_invalidate for updated issues.")
    else:
        print("No changes made.")


if __name__ == "__main__":
    main()
