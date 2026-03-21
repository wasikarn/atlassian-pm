---
name: update-doc
disable-model-invocation: true
x-compatibility: [mcp-confluence]
description: |
  Update an existing Confluence page with a 5-phase workflow
  Supports: content update, section update, status change, move

  Triggers: "update doc", "edit doc", "update confluence", "move page"
argument-hint: "[page-id or title] [--move parent-id]"
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

**⚠️ IMPORTANT: Fix Code Blocks (mandatory if content has code blocks)**

MCP markdown → Confluence will render code blocks as `<pre class="highlight">` which is incorrect.
**You must run the fix script immediately after every create/update:**

```bash
python3 .claude/skills/scripts/api/fix_confluence_code_blocks.py \
  --page-id [page_id]
```

The script will automatically convert `<pre class="highlight">` → `<ac:structured-macro ac:name="code">`.

**Option B: Find & replace**

```bash
python3 .claude/skills/scripts/api/update_confluence_page.py \
  --page-id [page_id] \
  --find "[old text]" \
  --replace "[new text]"
```

**Option C: Move page**

```bash
python3 .claude/skills/scripts/api/move_confluence_page.py \
  --page-id [page_id] \
  --parent-id [target_parent_id]
```

Batch move:

```bash
python3 .claude/skills/scripts/api/move_confluence_page.py \
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

## References

- Space: `{{PROJECT_KEY}}`
- MCP Tool: `confluence_update_page`, `confluence_get_page`
- Scripts: `.claude/skills/scripts/api/`
- [Tech Note Template](../../../references/templates-technote.md) - Tech Note best practices
- [Error Handling](references/error-handling.md)
- [Examples](references/examples.md)
