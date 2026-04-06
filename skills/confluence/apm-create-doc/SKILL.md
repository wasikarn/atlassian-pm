---
name: apm-create-doc
context: fork
agent: general-purpose
x-compatibility: [mcp-atlassian, mcp-confluence]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_create_remote_issue_link, mcp__mcp-atlassian__confluence_create_page, mcp__mcp-atlassian__confluence_get_page, mcp__mcp-atlassian__confluence_search
description: |
  This skill should be used when creating a new Confluence page from template. Supports tech-spec, ADR, parent (category page), and PRD templates with a 4-phase workflow.
  
  Trigger phrases: "create doc", "technical spec", "ADR", "PRD", "product requirements", "new page", "create page", "create confluence", "สร้าง doc", "new confluence page"
  
  This skill should NOT be used for updating existing pages (use update-doc).
argument-hint: "[template] [title] [--parent page-id]"
effort: medium
---

# /atlassian-pm:apm-create-doc

**Role:** Developer / Tech Lead
**Output:** Confluence Page

## Templates

| Template | Use Case | Structure |
| --- | --- | --- |
| `tech-spec` | API design, Feature spec | Overview → Requirements → Design → API → Testing |
| `adr` | Architecture Decision | Context → Decision → Consequences |
| `parent` | Category/Parent page | Title → Description → Sub-pages table |
| `prd` | Product Requirements Document | Executive Summary → User Stories → FR → NFR → Success Criteria → Assumptions |

## Phases

### 1. Discovery

Ask user to gather information:

**If template not specified:**

```text
What type of Document do you want to create?
1. tech-spec - Technical Specification
2. adr - Architecture Decision Record
3. parent - Category/Parent page (group pages)
4. prd - Product Requirements Document
```

**Gather details by template:**

| Template | Required Info |
| --- | --- |
| `tech-spec` | Title, Overview, Related Jira issue |
| `adr` | Title, Context, Options considered |
| `parent` | Title, Description, Category type |
| `prd` | Feature title, Target audience, Related Epic/Jira issue |

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

### 2. Generate Content

Generate markdown content based on template

**tech-spec Template:** | **adr Template:** | **parent Template:**

> See [references/templates.md](references/templates.md) for tech-spec, adr, parent, and prd template bodies.
>
> **Note:** `{toc}` and `{children}` macros only render in Confluence — for parent pages that need macros, use the `update_page_storage.py` script

**Gate:** Content generated

### 3. Review

Show preview for user to review:

```text
## Document Preview

**Template:** [tech-spec/adr]
**Title:** [title]
**Space:** {{PROJECT_KEY}}

[Show markdown content]

Any changes needed before creating?
```

**Gate:** User approves content

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

**⚠️ IMPORTANT: Fix Code Blocks (mandatory after every create)**

MCP `confluence_create_page` always renders code blocks as `<pre class="highlight">` which is incorrect.
**Run the fix script immediately after every create — no exceptions:**

```bash
uv run scripts/api/fix_confluence_code_blocks.py --page-id [created_page_id]
```

The script converts `<pre class="highlight">` → `<ac:structured-macro ac:name="code">`. Run from project root.

**Output:**

```text
## ✅ Document Created: [Title]

**Template:** [type]
**Space:** {{PROJECT_KEY}}

🔗 [View in Confluence](URL)

→ Link to Jira: use MCP jira_create_remote_issue_link
```

## Common Scenarios

> See [references/examples.md](references/examples.md) for common command examples.

## Examples

### ✅ Good

```text
/create-doc tech-spec "Video Upload API v2"                          # template + clear title
/create-doc adr "Switch from REST to GraphQL for mobile"             # ADR with decision context
/create-doc parent "Backend Services" --parent 123456789             # category page under specific parent
/create-doc prd "Video Upload Feature"                                # PRD for stakeholder review
/create-doc prd "Auth Refactor" --parent 123456789                   # PRD nested under existing section
```

### ❌ Bad

```text
/create-doc "Video Upload API"          # missing template type — forces interactive prompt
/create-doc                             # no args — causes full interactive discovery flow
/create-doc tech-spec "{{PROJECT_KEY}}-42 notes"   # wrong skill — Jira issue descriptions use /create-story or /create-task
/create-doc adr "Cache Strategy"       # valid creation, but forgetting to run fix_confluence_code_blocks.py
                                        # after create — always mandatory, not optional (HR4)
```

**Common mistakes:**

- Omitting the template type forces a multi-step interactive prompt that wastes time — always specify `tech-spec`, `adr`, `parent`, or `prd` upfront
- Using `/create-doc` for Jira issue descriptions — this skill creates Confluence pages only; use `/create-story` or `/create-task` for Jira
- Creating a `tech-spec` without linking it back to the related Jira epic/story via `jira_create_remote_issue_link`
- Skipping `fix_confluence_code_blocks.py` after creation — MCP always renders code blocks as `<pre class="highlight">` (broken); run `uv run scripts/api/fix_confluence_code_blocks.py --page-id [id]` after every create

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)

## References

Space: `{{PROJECT_KEY}}` · MCP: `confluence_create_page` · Scripts: `scripts/api/`

[Tech Note Template](../../../references/templates-technote.md) · [Templates](references/templates.md) · [Examples](references/examples.md)

Related: `/update-doc` for updating existing pages
