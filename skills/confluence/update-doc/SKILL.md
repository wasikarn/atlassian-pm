---
name: update-doc
context: fork
agent: general-purpose
x-compatibility: [mcp-confluence]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__confluence_search, mcp__mcp-atlassian__confluence_get_page, mcp__mcp-atlassian__confluence_get_page_children, mcp__mcp-atlassian__confluence_update_page
description: |
  Update an existing Confluence page with a 5-phase workflow
  Supports: content update, section update, status change, move

  Triggers: "update doc", "edit doc", "update confluence", "move page", "แก้ไข confluence", "edit confluence page"
  Use when: updating or moving an existing Confluence page
  Do NOT use for: creating new pages (use create-doc)
argument-hint: "[page-id or title] [--move parent-id]"
effort: medium
---

# /update-doc

**Role:** Developer / Tech Lead
**Output:** Updated Confluence Page

## Update Types

| Type | Description | Use Case |
| --- | --- | --- |
| `content` | Update entire content | Major revision |
| `section` | Update specific section | Add/modify section |
| `status` | Change document status | Draft → Published |
| `replace` | Find and replace text | Batch text changes |
| `move` | Move to different parent | Reorganize hierarchy |

---

## Phases

### 1. Discovery

Ask user to identify the page:

**If page is not specified:**

```text
Which page do you want to update?
1. Specify Page ID (e.g. 123456789)
2. Search by title
```

**If searching by title:**

```python
confluence_search(query="title ~ \"[search term]\"", limit=5)
```

**Gather update details:**

| Update Type | Required Info |
| --- | --- |
| `content` | New content (markdown) |
| `section` | Section name, New content |
| `status` | New status value |
| `replace` | Find text, Replace text |
| `move` | Target parent page ID |

**If moving:**

```text
Which parent page do you want to move it under?
1. Specify Page ID
2. Search by title
```

**Gate:** Page identified + Update type determined

---

### 2. Fetch Current

Retrieve current content:

```python
confluence_get_page(
  page_id="[page_id]",
  convert_to_markdown=true,
  include_metadata=true
)
```

**Output:**

- Current content (markdown)
- Page title
- Version number
- Last updated

**Gate:** Current content retrieved

---

### 3. Generate Updates

Generate updated content based on update type:

**Content Update:**

- Replace all content
- Preserve structure and formatting

**Section Update:**

- Find the section to edit
- Replace only that section
- Preserve other sections

**Status Update:**

- Find the status field
- Change value (Draft/In Review/Published)

**Replace:**

- Find all occurrences
- Replace with new text
- Report count

**Move:**

- Do not modify content
- Change only the parent page
- Preserve page metadata

**Gate:** Updated content generated (or move target identified)

---

### 4. Review

Show preview for user to review:

```text
## Update Preview

**Page:** [Title]
**Page ID:** [page_id]
**Current Version:** [version]
**Update Type:** [type]

### Changes:
[Show diff or summary of changes]

Would you like to proceed?
```

**Gate:** User approves changes

---

### 5. Update

**Option A: Content update (MCP + fix code blocks)**

```python
confluence_update_page(
  page_id="[page_id]",
  title="[title]",
  content="[updated markdown]"
)
```

**⚠️ IMPORTANT: Fix Code Blocks (mandatory after every content update)**

MCP `confluence_update_page` always renders code blocks as `<pre class="highlight">` which is incorrect.
**Run the fix script immediately after every update — no exceptions:**

```bash
uv run scripts/api/fix_confluence_code_blocks.py --page-id [page_id]
```

The script converts `<pre class="highlight">` → `<ac:structured-macro ac:name="code">`. Run from project root.

**Option B: Find & replace**

```bash
uv run scripts/api/update_confluence_page.py \
  --page-id [page_id] \
  --find "[old text]" \
  --replace "[new text]"
```

**Option C: Move page**

```bash
uv run scripts/api/move_confluence_page.py \
  --page-id [page_id] \
  --parent-id [target_parent_id]
```

Batch move:

```bash
uv run scripts/api/move_confluence_page.py \
  --page-ids [page_id1],[page_id2],[page_id3] \
  --parent-id [target_parent_id]
```

**Output:**

```text
## ✅ Document Updated: [Title]

**Page ID:** [page_id]
**New Version:** [version + 1]
**Update Type:** [type]

🔗 [View in Confluence](URL)
```

---

## Decision Flow

```text
Update type?
    │
    ├─ Move → move_confluence_page.py --page-id --parent-id
    │
    ├─ Find/Replace → update_confluence_page.py
    │
    └─ Content/Section/Status
          │
          └─ MCP confluence_update_page
                │
                └─ Has code blocks?
                      │
                      ├─ No → Done ✅
                      │
                      └─ Yes → fix_confluence_code_blocks.py --page-id
                                (MANDATORY post-step)
```

---

## Common Scenarios

> See [references/examples.md](references/examples.md) for common command and tool examples.

---

## Error Handling

> See [references/error-handling.md](references/error-handling.md) for error causes and solutions.

---

## Examples

### ✅ Good

```text
/update-doc 123456789                                   # page ID — unambiguous, always preferred
/update-doc 123456789 --section "API Design"            # update a specific section only
/update-doc 123456789 --status published                # promote draft to published
/update-doc 123456789 --move 987654321                  # move page under a new parent by ID
```

### ❌ Bad

```text
/update-doc "Video Upload API"          # ambiguous title — may match wrong page if duplicates exist
/update-doc                             # no page identified — triggers slow interactive search
/update-doc 123456789                   # updating a page with ToC/Children macros via MCP —
                                        # HR4: use update_page_storage.py instead or macros render as raw XML
/update-doc 123456789 "new content"     # updating without reading current content first —
                                        # risks overwriting important sections not in scope
```

**Common mistakes:**

- Passing a page title instead of a page ID when the title is not unique — Confluence search can return the wrong page and you will overwrite it silently
- Attempting to add a Table of Contents or Children macro via MCP `confluence_update_page` — MCP HTML-escapes macros; use `update_page_storage.py` for any page that needs Confluence macros (HR4)
- Skipping Phase 2 (Fetch Current) and generating new content blind — sections not in the user's request get dropped
- Forgetting to run `fix_confluence_code_blocks.py` after a content update that includes code blocks — same HR4 rendering bug as creation

---

## 🎓 Domain Expert Notes

### Why This Approach

The mandatory Phase 2 (Fetch Current) before any write enforces the core evergreen documentation principle: never update content you haven't read. Documentation debt — broken references, dropped sections, silent overwrites — originates almost entirely from write-without-read patterns. The 5-phase workflow mirrors content lifecycle management: retrieve → diff → generate → review → commit.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Content Lifecycle Management — CLM (AIIM / Gartner framework) | Phases 2–5 (fetch → generate → review → update) | CLM defines 5 stages: Create → Review → Approve → Publish → Archive. This skill's 5-phase workflow maps directly: Fetch=Approve-gate (check for existing approved content), Generate=Create, QG=Review, Update=Publish. The 30% threshold (section vs. content update) approximates the CLM "change scope" boundary between an amendment and a new revision |
| Evergreen Documentation (Tom Johnson, *I'd Rather Be Writing*, 2015) | Phase 3 section-scoped updates | Johnson's evergreen principle: each section is independently stable; updates should scope to the changed section only, not touch unrelated stable sections. A section update touching >30% of total page content violates evergreen boundaries — it's a version revision, not an amendment |
| Keep a Changelog convention (Olivier Lacan, keepachangelog.com) | `status` update type | Status transitions (Draft → In Review → Published) are lifecycle events that warrant a human-readable summary. The 90-day stale threshold aligns with Lacan's "Unreleased" convention: content not updated in 90+ days is effectively unreleased — may not reflect current reality |
| Docs as Code version traceability (Anne Gentle, *Docs Like Code*, 2017) | Version number displayed in Phase 4 preview | Showing the current Confluence version number before write surfaces concurrent-edit risk. Gentle's principle: documentation changes should be as reviewable as code changes — the version display is the equivalent of `git status` before committing |

### Key Metrics

- **Page version drift:** If current version ≥ 10 and the last update was > 90 days ago, the page is a stale content candidate — flag for review before making incremental edits
- **Section preservation rate:** A `section` update should touch ≤ 30% of total page content; if more than 30% changes, use `content` update type and full review
- **Stale detection threshold:** Atlassian recommends a 6-month automation trigger for pages with no edits — pages beyond this window should be reviewed for accuracy before any update, not just patched
- **Concurrent edit risk:** Confluence version numbers increment on every save; if the version fetched in Phase 2 differs from the current version at Phase 5 write time, abort and re-fetch — this is the Confluence equivalent of a Git merge conflict

### Expert Decision Criteria

- If the page contains a `{toc}` or `{children}` macro anywhere → always use `update_page_storage.py`, never MCP `confluence_update_page` (HR4; MCP HTML-escapes macros to raw XML)
- If the update touches only 1–2 sentences in a known section → use `section` update, not `content` update; limits blast radius
- If the user says "rename" or "retitle" → treat as `content` update, not `replace`; title changes require `confluence_update_page` with the new title field, not a find/replace on body text
- If the page was last edited > 6 months ago → read the full content in Phase 2 and validate all external links and Jira references before updating; stale pages often contain broken issue links
- If moving a page that has children → move the parent only; Confluence automatically moves all descendants; do not batch-move children manually

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Sections silently dropped after content update | Phase 2 skipped; new content generated from user input alone | Always fetch first; diff generated content against fetched content before writing |
| Macros render as raw XML after update | MCP `confluence_update_page` HTML-escapes `<ac:…>` tags | Use `update_page_storage.py` for any page with ToC, Children, or Code macros (HR4) |
| Wrong page overwritten | Title search returned multiple matches; first result accepted without confirmation | Always prefer page ID over title; if title used, show all matches and require explicit selection |
| Concurrent edit lost | Version fetched in Phase 2 is stale by write time | Re-fetch immediately before write in high-traffic spaces; compare version numbers |
| Move breaks child page links | Children moved manually after parent move | Move only the parent; Confluence cascades to descendants automatically |

### Authoritative References

- **Midori / Atlassian — Confluence Content Lifecycle Management:** "Content lifecycle management clarifies who is notified of stale content and defines content owners per section" — the `status` update type is the primary mechanism for formalising lifecycle transitions in Confluence
- **Docsie — Evergreen Documentation (2025):** Evergreen content requires scoped, targeted updates rather than wholesale rewrites; the `section` update type is the operational implementation of this principle
- **Keep a Changelog (keepachangelog.com):** "Don't let your friends dump git logs into changelogs" — status transitions on a Confluence page should carry a human-readable summary of what changed and why, not just a version bump
- **Atlassian Community — Knowledge Base Best Practices:** Set a 6-month automation rule to flag pages not updated since that window; stale pages erode team trust in the entire knowledge base faster than missing pages do

---

## References

- Space: `{{PROJECT_KEY}}`
- MCP Tool: `confluence_update_page`, `confluence_get_page`
- Scripts: `scripts/api/` (run with `uv run scripts/api/<script>.py` from project root)
- [Tech Note Template](../../../references/templates-technote.md) - Tech Note best practices
- [Error Handling](references/error-handling.md)
- [Examples](references/examples.md)
