#!/usr/bin/env python3
"""Update BEP-3302 scope: add CacheService removal rationale + flush() warning.

Adds:
1. Warning panel about flush() = FLUSHDB danger in Scope Boundaries section
2. Rationale bullets in Phase 5 panel about complete removal decision
3. New bullet in "in scope" list about flush() removal

One-time script — idempotent (checks for existing text).
"""

import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/atlassian-scripts"))
from lib.auth import create_ssl_context, get_auth_header, load_credentials
from lib.jira_api import JiraAPI, derive_jira_url


def bold(text):
    return {"type": "text", "text": text, "marks": [{"type": "strong"}]}

def plain(text):
    return {"type": "text", "text": text}

def code(text):
    return {"type": "text", "text": text, "marks": [{"type": "code"}]}

def para(*parts):
    return {"type": "paragraph", "content": list(parts)}

def bullet_list(items):
    return {"type": "bulletList", "content": [
        {"type": "listItem", "content": [para(*item) if isinstance(item, (list, tuple)) else para(item)]}
        for item in items
    ]}


# --- New content ---

FLUSH_WARNING_PANEL = {
    "type": "panel",
    "content": [
        para(bold("⚠️ flush() = FLUSHDB — ต้องลบ ไม่ใช่ migrate")),
        para(
            code("CacheService.flush()"),
            plain(" เรียก "),
            code("FLUSHDB"),
            plain(" — ลบ "),
            bold("ทั้ง Redis database"),
            plain(" รวม OAT tokens, rate limit counters, OAuth state, campaign counters ทั้งหมด"),
        ),
        para(
            plain("ปัจจุบันมีแค่ Questionnaire admin ที่เรียก — "),
            bold("ต้องแทนที่ด้วย tag-based invalidation"),
            plain(" ไม่ใช่ migrate flush() ไป Bentocache"),
        ),
    ],
    "attrs": {"panelType": "error"},
}

REMOVAL_RATIONALE_BULLETS = [
    (bold("Decision: "), plain("ลบ CacheService ทั้งหมด — ไม่ rename/refactor ให้อยู่ร่วมกับ Bentocache")),
    (bold("เหตุผล 1: "), plain("ชื่อ CacheService ชนกับ Bentocache conceptually — สับสนว่าใครคือ cache ตัวจริง")),
    (bold("เหตุผล 2: "), plain("ทั้ง 16 callers ใช้ pattern เดียวกัน (manual get→set) — Bentocache "), code("getOrSet()"), plain(" แทนได้ 100%")),
    (bold("เหตุผล 3: "), code("remember()"), plain(" มีอยู่แต่ไม่มีใครเรียกใช้ — confirms low adoption ไม่จำเป็นต้อง preserve")),
    (bold("เหตุผล 4: "), code("flush()"), plain(" = "), code("FLUSHDB"), plain(" อันตราย — ลบทั้ง DB, ต้องถอดออกไม่ใช่ migrate")),
]


def has_text(content, search_text):
    """Recursively check if text exists anywhere in ADF content."""
    return search_text in json.dumps(content, ensure_ascii=False)


def find_section_index(content, section_text):
    """Find the index of a heading containing section_text."""
    for i, node in enumerate(content):
        if node.get("type") == "heading" and section_text in json.dumps(node):
            return i
    return -1


def find_panel_with_text(content, text, start_idx=0):
    """Find panel containing specific text after start_idx."""
    for i in range(start_idx, len(content)):
        node = content[i]
        if node.get("type") == "panel" and text in json.dumps(node, ensure_ascii=False):
            return i
    return -1


def add_scope_updates(content):
    """Add flush warning + removal rationale to BEP-3302 description."""
    changes = []

    # 1. Find "Scope Boundaries" section (section 5)
    scope_idx = find_section_index(content, "Scope Boundaries")
    if scope_idx == -1:
        print("  WARNING: Scope Boundaries section not found")
        return content, changes

    # 2. Find the note panel (scope in/out) after Scope Boundaries
    scope_panel_idx = find_panel_with_text(content, "อะไรอยู่ใน scope", scope_idx)
    if scope_panel_idx == -1:
        print("  WARNING: Scope panel not found")
        return content, changes

    # 3. Add flush warning panel BEFORE the scope panel
    if not has_text(content, "FLUSHDB"):
        content.insert(scope_panel_idx, FLUSH_WARNING_PANEL)
        changes.append("Added flush() = FLUSHDB warning panel")
        # Adjust indices after insertion
        scope_panel_idx += 1

    # 4. Add removal rationale to scope panel's "in scope" bullet list
    scope_panel = content[scope_panel_idx]
    panel_content = scope_panel.get("content", [])

    # Find the "in scope" bullet list
    for j, pnode in enumerate(panel_content):
        if pnode.get("type") == "bulletList":
            items = pnode.get("content", [])
            # Check if we already added the new items
            if not has_text(items, "flush"):
                items.append({
                    "type": "listItem",
                    "content": [para(
                        code("flush()"),
                        plain(" removal — ไม่ migrate, แทนด้วย tag-based invalidation"),
                    )]
                })
                changes.append("Added flush() removal to in-scope list")
            break

    # 5. Find Phase 5 panel and add rationale
    phase5_idx = find_panel_with_text(content, "Phase 5")
    if phase5_idx == -1:
        print("  WARNING: Phase 5 panel not found")
        return content, changes

    phase5_panel = content[phase5_idx]
    p5_content = phase5_panel.get("content", [])

    if not has_text(p5_content, "Decision:"):
        # Add a rule + rationale paragraph + bullets after existing content
        p5_content.append(para(bold("Removal Rationale (Feb 2026 decision):")))
        p5_content.append(bullet_list(REMOVAL_RATIONALE_BULLETS))
        changes.append("Added removal rationale to Phase 5 panel")

    return content, changes


def main():
    dry_run = "--dry-run" in sys.argv
    issue_key = "BEP-3302"

    creds = load_credentials()
    api = JiraAPI(
        base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context(),
    )

    print(f"=== Updating {issue_key} Scope ===")
    if dry_run:
        print("(DRY RUN mode)")

    issue = api.get_issue(issue_key)
    desc = issue["fields"].get("description")
    if not desc:
        print("  No description found")
        sys.exit(1)

    content = deepcopy(desc.get("content", []))

    # Idempotency check
    if has_text(content, "FLUSHDB") and has_text(content, "Decision:"):
        print("  Already updated — skipping")
        return

    content, changes = add_scope_updates(content)

    if not changes:
        print("  No changes needed")
        return

    print(f"  Changes: {', '.join(changes)}")

    if dry_run:
        print(f"  DRY RUN — would apply {len(changes)} changes")
        return

    updated_desc = {"type": "doc", "version": 1, "content": content}
    status = api.update_description(issue_key, updated_desc)

    if status in (200, 204):
        print(f"  {issue_key}: Updated successfully")
    else:
        print(f"  {issue_key}: Update failed (HTTP {status})")
        sys.exit(1)


if __name__ == "__main__":
    main()
