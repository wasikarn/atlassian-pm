# Troubleshooting Guide

## acli Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `unknown field "project"` | Wrong field name | Use `projectKey` not `project` |
| `unknown field "parent"` | acli doesn't support parent | Two-Step: MCP create + acli edit |
| `missing required field` | Incomplete JSON | Check all required fields |
| `issues field required` | Edit without issue key | Add `"issues": ["ABC-XXX"]` for edits |
| `Invalid document structure` | Malformed ADF | Check `type: "doc"` at root |
| `Unknown node type` | Typo in type | Verify: heading, paragraph, bulletList, etc. |
| `Invalid attrs` | Wrong attributes | panel: `panelType` / heading: `level` |
| `Nested table error` | Tables in tables | ❌ Use bullets instead |
| `INVALID_INPUT` (InvalidPayloadException) | Nested bulletList | `listItem > bulletList` not allowed — flatten |
| `401 Unauthorized` | Invalid token | `acli auth login` |
| `403 Forbidden` | No permission | Check project permissions |

> CREATE has no `"issues"` field — EDIT requires `"issues": ["ABC-XXX"]`

### Subtask Two-Step Workflow

MCP create → acli edit. Parent format: Subtask = `{"parent": {"key": "ABC-XXX"}}` (object) · Epic child = `{"parent": "ABC-2883"}` (string).

```bash
# Step 2: push description via acli
acli jira workitem edit --from-json {{artifacts_dir}}/subtask.json --yes
```

## MCP Tool Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `JQL syntax error` | Invalid query | Check JQL operators/field names |
| `Expecting ')' but got 'ORDER'` | ORDER BY with `parent =` | Use `"Parent Link" = ABC-XXX ORDER BY...` |
| `key in (...) ORDER BY` → parse error | ORDER BY not allowed with `key in` | Remove `ORDER BY` |
| `Field not found` | Wrong field name | Use `issuetype` not `type` |
| `Issue not found` | Wrong key | Verify format: `ABC-XXX` |
| `Rate limited` | Too many requests | Wait and retry |
| `exceeds maximum allowed tokens` | Too much data | `fields="summary,status,description,issuetype,parent"` + `comment_limit=5` |
| `jira_update_issue` parent → silent fail | MCP doesn't set parent | REST: `api._request('PUT', '/rest/api/3/issue/KEY', {'fields': {'parent': {'key': 'EPIC-KEY'}}})` |
| `jira_create_issue` parent → silent fail | MCP may ignore parent | Verify after create; use REST if needed |
| `jira_update_issue(fields=...)` → unexpected kwarg | Wrong param name | Use `additional_fields` not `fields` |
| `jira_get_agile_boards(project_key_or_id=...)` → unexpected kwarg | Wrong param name | Use `project_key` not `project_key_or_id` |
| `jira_get_sprint_issues` limit > 50 → error | Exceeds max | Max `limit=50` — paginate with `start_at` |
| `jira_update_issue` assignee → silent fail | MCP doesn't set assignee | `acli jira workitem assign -k "KEY" -a "email" -y` |
| `acli workitem assign -a ""` → failed to resolve | Empty string invalid | `acli jira workitem assign -k "KEY" --remove-assignee -y` |
| `acli jira issue update --assignee` → unknown flag | Wrong command | Use `acli jira workitem assign` |
| `expected 'key' to be string` / `parent not specified` | Wrong parent format | `additional_fields={"parent": {"key": "ABC-XXX"}}` — object, not string |
| Subtask + sprint field → `cannot be associated to a sprint` | Subtasks inherit sprint | Remove sprint field — inherited from parent |
| MCP `sprint: null` doesn't work | MCP can't remove sprint | Agile REST: `POST /rest/agile/1.0/backlog/issue` + numeric IDs |
| Agile API issue key → 204 but no move | Key not accepted | Use numeric ID from `issue["id"]` |
| Sprint field `{"id": N}` → error | Wrong format | `{{SPRINT_FIELD}}` accepts plain number: `{"{{SPRINT_FIELD}}": 123}` |
| Issue link "Relates to" → error | Wrong link type | Correct: `"Relates"` / valid: `Blocks`, `Duplicate`, `Cloners` |
| `Sibling tool call errored` | One parallel call failed → all cancelled | Fix failing call first; validate JQL before parallel execution |

## Common Workflow Errors

| Phase | Issue | Solution |
| --- | --- | --- |
| Discovery | Can't find parent Epic | `project = {{PROJECT_KEY}} AND type = Epic` |
| Design | Generic file paths | **Explore codebase first** — use Task(Explore) |
| Design | Wrong service tag | `[BE]`, `[FE-Admin]`, `[FE-Web]` |
| Create | acli create fails | Validate JSON/ADF structure |
| Create | Wrong issue type | `Story`, `Sub-task`, `Epic` (exact case) |
| Update | Edit overwrites content | Fetch current first, then merge |

## Confluence & Mermaid Errors

Full details: `mermaid-guide.md` + `.claude/rules/mermaid.md`

| Issue | Fix |
| --- | --- |
| Code blocks not highlighted | `fix_confluence_code_blocks.py --page-id` |
| Macros as text | `update_page_storage.py` |
| Cannot move page | `move_confluence_page.py` |
| Mermaid not rendering | Code block + Forge `ac:adf-extension` macro (see `mermaid-guide.md`) |
| "Error loading extension!" on panels | `fix_confluence_panels.py --page-id` |
| `401 Unauthorized` (scripts) | Check `~/.config/atlassian/.env` |

## Quick Fixes

| Problem | Fix |
| --- | --- |
| Description ugly format | Use `acli --from-json` not MCP |
| Inline code not rendering | `marks: [{"type": "code"}]` |
| Panel wrong color | info (blue), success (green), warning (yellow), error (red) |

**Related:** ADF format: `templates.md` · Tool selection: `tools.md` · Scripts: `../scripts/docs/README.md`
