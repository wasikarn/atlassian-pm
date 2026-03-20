# Tool Selection Guide

## Decision Flow

```text
What do you need?
    │
    ├─ Create/Update Jira issue description
    │     │
    │     └─ Always use acli + --from-json (ADF)
    │           • Create JSON file with ADF content
    │           • acli jira workitem create --from-json issue.json
    │           • acli jira workitem edit --from-json issue.json --yes
    │
    ├─ Update other fields (not description)
    │     └─ MCP jira_update_issue is OK
    │
    ├─ Search Jira/Confluence
    │     └─ MCP jira_search / confluence_search
    │
    ├─ Read Jira issue
    │     └─ MCP jira_get_issue
    │
    ├─ Explore codebase
    │     └─ Task tool with Explore agent
    │
    └─ Confluence page
          ├─ Read  → MCP confluence_get_page
          ├─ Create (no code) → MCP confluence_create_page
          ├─ Create (with code) → Python script
          ├─ Update content → Python script
          ├─ Move page → Python script
          └─ Add macros (ToC, Children) → Python script
```

---

## Tool Reference

### Jira Operations

| Operation | Tool | Command/Syntax |
| --- | --- | --- |
| **Search issues** | MCP | `jira_search(jql: "project = BEP AND ...")` |
| **Get issue details** | MCP | `jira_get_issue(issue_key: "ABC-XXX", fields: "summary,status,description")` |

> ⚠️ **IMPORTANT:** Always use the `fields` parameter to prevent token limit errors!
>
> ```python
> # ❌ Bad - may exceed token limit if the issue has too much data
> jira_get_issue(issue_key="ABC-XXX")
>
> # ✅ Good - specify only the fields you need
> jira_get_issue(
>     issue_key="ABC-XXX",
>     fields="summary,status,description,issuetype,parent",
>     comment_limit=5
> )
> ```

| **Create issue** | acli | `acli jira workitem create --from-json file.json` |
| **Update description** | acli | `acli jira workitem edit --from-json file.json --yes` |
| **Update other fields** | MCP | `jira_update_issue(issue_key: "ABC-XXX", fields: {...})` |
| **Assign issue** | acli | `acli jira workitem assign -k "ABC-XXX" -a "email@..." -y` |
| **Create issue link** | MCP | `jira_create_issue_link(link_type: "Relates", inward_issue: "ABC-X", outward_issue: "ABC-Y")` |
| **Get transitions** | MCP | `jira_get_transitions(issue_key: "ABC-XXX")` |
| **Transition issue** | MCP | `jira_transition_issue(issue_key: "ABC-XXX", ...)` |
| **Set dates** | MCP | `jira_update_issue(issue_key: "ABC-XXX", additional_fields: {"{{START_DATE_FIELD}}": "YYYY-MM-DD", "duedate": "YYYY-MM-DD"})` |
| **Set story points** | MCP | `jira_update_issue(issue_key: "ABC-XXX", additional_fields: {"customfield_10016": 5})` |
| **Set size** | MCP | `jira_update_issue(issue_key: "ABC-XXX", additional_fields: {"customfield_10107": {"value": "M"}})` |
| **Set original estimate** | MCP | `jira_update_issue(issue_key: "ABC-XXX", additional_fields: {"timetracking": {"originalEstimate": "4h"}})` |
| **Move to sprint** | MCP | `jira_update_issue(issue_key: "ABC-XXX", additional_fields: {"{{SPRINT_FIELD}}": 123})` |
| **Get sprints** | MCP | `jira_get_sprints_from_board(board_id: "2", state: "future")` |

> **BEP Board/Sprint Info:** Board ID `2` · Use `jira_get_sprints_from_board` to get current Sprint IDs
> Date fields: `{{START_DATE_FIELD}}` (Start), `duedate` (Due) · Sprint field: `{{SPRINT_FIELD}}` (plain number)
> Estimation fields: `customfield_10016` (Story Points, numeric), `customfield_10107` (Size, select: XS/S/M/L/XL), `timetracking` (Original Estimate, format: "1d"/"4h"/"30m")
>
> **Issue Link Types (BEP):** `Relates` · `Blocks` · `Duplicate` · `Cloners` · `Test Case`
> ⚠️ Use `"Relates"` not `"Relates to"` — name must match Jira config
>
> ⚠️ **MCP assignee bug:** `jira_update_issue` assignee field reports success but doesn't update.
> Use `acli jira workitem assign -k "KEY" -a "email" -y` instead.

### Confluence Operations

| Operation | Tool | Command/Syntax |
| --- | --- | --- |
| **Search pages** | MCP | `confluence_search(query: "...")` |
| **Get page** | MCP | `confluence_get_page(page_id: "...")` |
| **Create page (simple)** | MCP | `confluence_create_page(space_key: "{{PROJECT_KEY}}", ...)` |
| **Create page (code blocks)** | Script | `python3 .claude/scripts/api/create_confluence_page.py` |
| **Update content** | Script | `python3 .claude/scripts/api/create_confluence_page.py --page-id` |
| **Find/Replace text** | Script | `python3 .claude/scripts/api/update_confluence_page.py` |
| **Move page** | Script | `python3 .claude/scripts/api/move_confluence_page.py` |
| **Add macros (ToC, Children)** | Script | `python3 .claude/scripts/api/update_page_storage.py` |

> ⚠️ **IMPORTANT:** MCP `confluence_create_page` and `confluence_update_page` have limitations:
>
> - Code blocks will render incorrectly (no syntax highlighting)
> - Macros (ToC, Children, Status) will render as plain text instead
> - Use the Python scripts in `.claude/scripts/api/` instead

### Confluence Scripts Decision Flow

```text
What do you need to do?
    │
    ├─ Create new page (no code)
    │     └─ MCP confluence_create_page
    │
    ├─ Create new page (with code blocks)
    │     └─ create_confluence_page.py --space --title
    │
    ├─ Update all content
    │     └─ create_confluence_page.py --page-id --content-file
    │
    ├─ Find/Replace text
    │     └─ update_confluence_page.py --find --replace
    │
    ├─ Move page(s) to new parent
    │     └─ move_confluence_page.py --page-id(s) --parent-id
    │
    └─ Add macros (ToC, Children, Status)
          └─ update_page_storage.py --page-id --content-file
```

**Script Location:** `.claude/scripts/api/`

**Full Documentation:** `.claude/skills/utilities/atlassian-scripts/SKILL.md`

### Codebase Exploration

| Operation | Tool | Syntax |
| --- | --- | --- |
| **Deep exploration** | Task | `Task(subagent_type: "Explore", prompt: "...")` |
| **Quick file search** | Glob | `Glob(pattern: "**/*.tsx")` |
| **Code search** | Grep | `Grep(pattern: "functionName")` |
| **Read file** | Read | `Read(file_path: "/path/to/file")` |

---

## acli Commands

```bash
# Create new issue
acli jira workitem create --from-json {{artifacts_dir}}/bep-xxx.json

# Update existing issue (requires "issues": ["ABC-XXX"] in JSON)
acli jira workitem edit --from-json {{artifacts_dir}}/bep-xxx.json --yes

# List issues
acli jira workitem list --project BEP --limit 10

# Get issue details
acli jira workitem get ABC-XXX
```

---

## Effort Sizing

> Canonical size guide: [templates-story.md](templates-story.md#story-best-practices)

| Size | Duration | Hours | SP | Action |
| --- | --- | --- | --- | --- |
| XS | < 0.5 day | < 4h | 1 | Single sub-task |
| S | 0.5-1 day | 4-8h | 2 | Single sub-task |
| M | 1-2 days | 8-16h | 3 | Single sub-task — Ideal |
| L | 2-4 days | 16-32h | 5 | Consider splitting (SPIDR) |
| XL | > 4 days | > 32h | 8 | Must split — use SPIDR |

---

## See Also

> Detailed references are in separate files — load when needed

- **ADF format** (CREATE vs EDIT, panels, tables, inline code) → [templates.md](templates.md)
- **JQL patterns** (search, filter, operators) → [jql-quick-ref.md](jql-quick-ref.md)
- **Error recovery** (workflow errors, validation) → [troubleshooting.md](troubleshooting.md)
