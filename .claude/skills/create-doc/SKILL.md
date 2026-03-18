---
name: create-doc
disable-model-invocation: true
compatibility: [mcp-atlassian, mcp-confluence]
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

**tech-spec Template:**

```markdown
# [Title] - Technical Specification

## Overview
[Brief description of what this spec covers]

## Related Issues
- [{{PROJECT_KEY}}-XXX](https://{{JIRA_SITE}}/browse/BEP-XXX)

---

## Requirements

### Functional Requirements
- FR-1: [Requirement]
- FR-2: [Requirement]

### Non-Functional Requirements
- NFR-1: [Performance/Security/etc.]

---

## Design

### Architecture
[High-level architecture description]

### Data Model
[Database changes if any]

### Sequence Diagram
[Flow description or diagram]

---

## API Specification

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/resource | Create resource |
| GET | /api/v1/resource/:id | Get resource |

### Request/Response Examples
[Code examples]

---

## Testing Strategy

### Unit Tests
- [Test case 1]

### Integration Tests
- [Test case 1]

### Manual Testing
- [Test scenario 1]

---

## Rollout Plan
1. Deploy to staging
2. QA verification
3. Deploy to production

## Rollback Plan
[How to rollback if issues arise]
```

**adr Template:**

```markdown
# ADR-XXX: [Title]

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
[What is the issue that we're seeing that is motivating this decision?]

## Decision
[What is the change that we're proposing and/or doing?]

## Options Considered

### Option 1: [Name]
**Pros:**
- [Pro 1]

**Cons:**
- [Con 1]

### Option 2: [Name]
**Pros:**
- [Pro 1]

**Cons:**
- [Con 1]

## Consequences

### Positive
- [Positive consequence 1]

### Negative
- [Negative consequence 1]

## Related
- [Link to related ADRs or issues]
```

**parent Template:**

```markdown
# [Title]

[Brief description of what this category contains]

{toc:maxLevel=2}

---

## 📄 Sub-pages

{children:all=true|sort=title}

---

## 🏷️ Topics Covered

| Topic | Description |
| --- | --- |
| [Topic 1] | [Description] |
| [Topic 2] | [Description] |

---

## 🔗 Related

- [Link to related pages or issues]

---

*Last updated: [date]*
```

> **Note:** `{toc}` and `{children}` macros only render in Confluence
> For parent pages that need macros, use the `update_page_storage.py` script

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
python3 .claude/skills/atlassian-scripts/scripts/fix_confluence_code_blocks.py \
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

| Scenario | Command |
| --- | --- |
| Create Tech Spec | `/create-doc tech-spec "Payment API"` |
| Create ADR | `/create-doc adr "Use Redis for caching"` |
| Create Parent page | `/create-doc parent "Documentation: Ads System"` |
| Create as child | `/create-doc tech-spec "API Spec" --parent 987654321` |

---

## References

- Space: `BEP`
- MCP Tool: `confluence_create_page`
- Scripts: `.claude/skills/atlassian-scripts/scripts/`
- [Tech Note Template](../shared-references/templates-technote.md) - Tech Note best practices
- Related: `/update-doc` for updating existing pages
