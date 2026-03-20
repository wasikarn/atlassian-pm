---
name: create-doc
disable-model-invocation: true
x-compatibility: [mcp-atlassian, mcp-confluence]
description: |
  Create Confluence page from template with a 4-phase workflow
  Supports: tech-spec, adr, parent (category page)

  Triggers: "create doc", "technical spec", "ADR"
argument-hint: "[template] [title] [--parent page-id]"
---

# /create-doc

**Role:** Developer / Tech Lead
**Output:** Confluence Page

## Templates

| Template | Use Case | Structure |
| --- | --- | --- |
| `tech-spec` | API design, Feature spec | Overview → Requirements → Design → API → Testing |
| `adr` | Architecture Decision | Context → Decision → Consequences |
| `parent` | Category/Parent page | Title → Description → Sub-pages table |

---

## Phases

### 1. Discovery

Ask user to gather information:

**If template not specified:**

```text
What type of Document do you want to create?
1. tech-spec - Technical Specification
2. adr - Architecture Decision Record
3. parent - Category/Parent page (group pages)
```

**Gather details by template:**

| Template | Required Info |
| --- | --- |
| `tech-spec` | Title, Overview, Related Jira issue |
| `adr` | Title, Context, Options considered |
| `parent` | Title, Description, Category type |

**If creating as child of another page:**

```text
Which parent page do you want to create under?
1. Root (no parent)
2. Specify Page ID
3. Search by title
```

**Search for parent page:**

```python
confluence_search(query="title ~ \"[search term]\"", limit=5)
```

**Gate:** User provides required info + Parent page identified (if specified)

---

### 2. Generate Content

Generate markdown content based on template

**tech-spec Template:** | **adr Template:** | **parent Template:**

> See [references/templates.md](references/templates.md) for tech-spec, adr, and parent template bodies.
>
> **Note:** `{toc}` and `{children}` macros only render in Confluence — for parent pages that need macros, use the `update_page_storage.py` script

**Gate:** Content generated

---

### 3. Review

Show preview for user to review:

```text
## Document Preview

**Template:** [tech-spec/adr]
**Title:** [title]
**Space:** BEP

[Show markdown content]

Any changes needed before creating?
```

**Gate:** User approves content

---

### 4. Create

Create page with MCP tool:

```python
confluence_create_page(
  space_key="{{PROJECT_KEY}}",
  title="[Title]",
  content="[markdown content]",
  parent_id="[optional parent page ID]"
)
```

**⚠️ IMPORTANT: Fix Code Blocks (mandatory if content has code blocks)**

MCP markdown → Confluence will render code blocks as `<pre class="highlight">` which is incorrect.
**You must run the fix script immediately after every create/update:**

```bash
python3 .claude/skills/scripts/api/fix_confluence_code_blocks.py \
  --page-id [created_page_id]
```

The script will automatically convert `<pre class="highlight">` → `<ac:structured-macro ac:name="code">`.

**Output:**

```text
## ✅ Document Created: [Title]

**Template:** [type]
**Space:** BEP

🔗 [View in Confluence](URL)

→ Link to Jira: use MCP jira_create_remote_issue_link
```

---

## Common Scenarios

> See [references/examples.md](references/examples.md) for common command examples.

---

## References

- Space: `BEP`
- MCP Tool: `confluence_create_page`
- Scripts: `.claude/skills/scripts/api/`
- [Tech Note Template](../../../references/templates-technote.md) - Tech Note best practices
- [Templates](references/templates.md)
- [Examples](references/examples.md)
- Related: `/update-doc` for updating existing pages
