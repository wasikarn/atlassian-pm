---
name: create-doc
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [mcp-atlassian, mcp-confluence]
description: |
  Create Confluence page from template with a 4-phase workflow
  Supports: tech-spec, adr, parent (category page)

  Triggers: "create doc", "technical spec", "ADR"
argument-hint: "[template] [title] [--parent page-id]"
effort: medium
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
**Space:** {{PROJECT_KEY}}

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
**Space:** {{PROJECT_KEY}}

🔗 [View in Confluence](URL)

→ Link to Jira: use MCP jira_create_remote_issue_link
```

---

## Common Scenarios

> See [references/examples.md](references/examples.md) for common command examples.

---

## Examples

### ✅ Good

```text
/create-doc tech-spec "Video Upload API v2"                          # template + clear title
/create-doc adr "Switch from REST to GraphQL for mobile"             # ADR with decision context
/create-doc parent "Backend Services" --parent 123456789             # category page under specific parent
/create-doc tech-spec "Auth Refactor" --parent 987654321             # spec nested under existing section
```

### ❌ Bad

```text
/create-doc "Video Upload API"          # missing template type — forces interactive prompt
/create-doc                             # no args — causes full interactive discovery flow
/create-doc tech-spec "{{PROJECT_KEY}}-42 notes"   # wrong skill — Jira issue descriptions use /create-story or /create-task
/create-doc adr "Cache Strategy"       # valid creation, but forgetting to run fix_confluence_code_blocks.py
                                        # after if the ADR body contains code blocks (HR4 violation)
```

**Common mistakes:**

- Omitting the template type forces a multi-step interactive prompt that wastes time — always specify `tech-spec`, `adr`, or `parent` upfront
- Using `/create-doc` for Jira issue descriptions — this skill creates Confluence pages only; use `/create-story` or `/create-task` for Jira
- Creating a `tech-spec` without linking it back to the related Jira epic/story via `jira_create_remote_issue_link`
- Skipping `fix_confluence_code_blocks.py` after creation when the page contains code blocks — MCP renders them as `<pre class="highlight">` (broken), not the proper Confluence code macro

---

## 🎓 Domain Expert Notes

### Why This Approach

The 3-template system (tech-spec / adr / parent) directly maps to the Diátaxis/Divio documentation framework's principle that each document type serves a distinct cognitive mode — reference (tech-spec), decision record (adr), and navigation (parent). Mixing types in a single page is the most common cause of documentation that exists but cannot be found or trusted.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Diátaxis (Divio) | Template selection in Phase 1 | Forces single-purpose pages; one type = one cognitive job |
| ADR (MADR format) | `adr` template structure | Context → Decision → Consequences captures *why*, not just *what*; prevents decisions being relitigated |
| Docs as Code | Jira link step in Phase 4 output | Traceability from requirement (Jira) to design doc (Confluence) mirrors code→PR→ticket linkage |
| Information Architecture 5–9 rule | `parent` template use | Research shows 5–9 top-level categories is the optimal range for human navigation; creating parent pages is the primary mechanism to stay within that range as a space grows |

### Key Metrics

- **Page findability:** Target ≤ 3 clicks from space root to any page — exceeding this indicates missing parent pages or flat structure
- **ADR completeness:** Every ADR must contain at least one rejected alternative with documented rationale; ADRs without rejected options are opinions, not decisions
- **Jira linkage rate:** 100% of `tech-spec` pages should link back to a Jira epic or story via `jira_create_remote_issue_link` — unlinked specs become orphaned and unmaintained
- **Flesch-Kincaid target:** Technical docs aimed at a developer audience should score Grade 10–12; above Grade 14 signals sentences are too long and should be split

### Expert Decision Criteria

- If the user's request contains "why did we" or "we need to decide" → `adr`, not `tech-spec`
- If the user's request is about how a system *will* work → `tech-spec`
- If the request is to create a space section for a team or service area → `parent` first, then nest `tech-spec`/`adr` beneath it
- If the title contains a version number (e.g. "API v2") → this is a `tech-spec`; version-named ADRs are an anti-pattern because decisions should be immutable once recorded
- ADRs must never be deleted or substantially edited after acceptance — append a superseding ADR instead and link them bidirectionally

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Tech spec becomes a meeting notes dump | No enforced template sections; sections like "Overview" feel optional | Make all sections mandatory in Phase 2; leave section headers with `TBD` if unknown rather than omitting them |
| ADR relitigated 6 months later | Missing "rejected options" section; team doesn't know what was considered | Enforce at least one alternative with "Why not chosen" before approving |
| Confluence space becomes a flat list of 200 pages | Parent pages created too late or not at all | Create parent pages proactively at space setup; use the 5–9 top-level rule as a forcing function |
| Code blocks render as `<pre class="highlight">` | MCP `confluence_create_page` emits raw HTML, not Confluence storage format macros | Always run `fix_confluence_code_blocks.py` post-create (already in Phase 4) — never skip |
| Spec linked to wrong Jira issue | Linked via text copy-paste instead of `jira_create_remote_issue_link` | Use remote link API; it creates a bi-directional "Confluence pages" panel in Jira automatically |

### Authoritative References

- **Diátaxis (Procida, 2017–2025):** "The problem with most documentation is not that it is badly written, but that it tries to do too many things at once." — each page must serve exactly one of the four modes
- **joelparkerhenderson/architecture-decision-record (GitHub):** The most widely adopted ADR template collection; MADR format is recommended for Confluence because its tabular "Considered Options" section renders cleanly
- **Atlassian Confluence Best Practices Guide:** Start with broad categories (5–9 max), become more specific as you go deeper — the taxonomy should reflect how readers search, not how the org chart is drawn
- **Keep a Changelog (keepachangelog.com):** "Changelogs are for humans, not machines" — the same principle applies to ADRs; write for the engineer in 18 months, not the one who wrote it today

---

## References

- Space: `{{PROJECT_KEY}}`
- MCP Tool: `confluence_create_page`
- Scripts: `.claude/skills/scripts/api/`
- [Tech Note Template](../../../references/templates-technote.md) - Tech Note best practices
- [Templates](references/templates.md)
- [Examples](references/examples.md)
- Related: `/update-doc` for updating existing pages
