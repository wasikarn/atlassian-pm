# Troubleshooting Guide

> Universal error recovery for jira-workflow commands

## acli Errors

### JSON Format Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `unknown field "project"` | Wrong field name | Use `projectKey` not `project` |
| `unknown field "parent"` | acli does not support the parent field | Use Two-Step Workflow: MCP create + acli edit |
| `missing required field` | Incomplete JSON | Check all required fields present |
| `invalid JSON syntax` | Malformed JSON | Validate JSON structure |
| `issues field required` | Edit without issue key | Add `"issues": ["ABC-XXX"]` for edits |

**Create vs Edit JSON:**

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Story",
  "summary": "..."
}
```

Note: CREATE has no "issues" field, EDIT requires `"issues": ["ABC-XXX"]`.

### Subtask Creation (Two-Step Workflow)

> ⚠️ **Getting `unknown field "parent"`?** Use this workflow

**Step 1: Create shell with MCP**

```typescript
// Subtask — parent is an object
jira_create_issue({
  project_key: "{{PROJECT_KEY}}",
  summary: "[TAG] - Description",
  issue_type: "Subtask",
  additional_fields: { parent: { key: "ABC-XXX" } }
})

// Epic child (Story/Task) — parent is a string
jira_create_issue({
  project_key: "{{PROJECT_KEY}}",
  summary: "Story title",
  issue_type: "Story",
  additional_fields: { parent: "ABC-2883" }
})
```

> ⚠️ **Parent format:** Subtask = `{parent: {key: "ABC-XXX"}}` (object) / Epic child = `{parent: "ABC-2883"}` (string)

**Step 2: Update description with acli**

```json
{
  "issues": ["ABC-YYY"],
  "description": { "type": "doc", "version": 1, "content": [...] }
}
```

```bash
acli jira workitem edit --from-json {{artifacts_dir}}/subtask.json --yes
```

### Authentication Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `401 Unauthorized` | Invalid token | Re-authenticate: `acli auth login` |
| `403 Forbidden` | No permission | Check project permissions |
| `Token expired` | Session timeout | Re-run `acli auth login` |

### ADF Validation Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `Invalid document structure` | Malformed ADF | Check `type: "doc"` at root |
| `Unknown node type` | Typo in type name | Verify: heading, paragraph, bulletList, etc. |
| `Invalid attrs` | Wrong attributes | Check panel: `panelType`, heading: `level` |
| `Nested table error` | Tables in tables | ❌ Tables cannot contain tables - use bullets |
| `INVALID_INPUT` (InvalidPayloadException) | Nested bulletList | listItem > bulletList is not allowed - flatten or use comma-separated text |

**ADF Structure Must Have:**

```json
{
  "description": {
    "type": "doc",
    "version": 1,
    "content": []
  }
}
```

## MCP Tool Errors

### Search Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `JQL syntax error` | Invalid query | Check JQL operators and field names |
| `Expecting ')' but got 'ORDER'` | ORDER BY with parent query | Use `"Parent Link" = ABC-XXX ORDER BY...` instead of `parent = ABC-XXX ORDER BY...` |
| `key in (...) ORDER BY` → parse error | ORDER BY not allowed with key in | Remove `ORDER BY` when using `key in (...)` syntax |
| `Field not found` | Wrong field name | Use `issuetype` not `type` for search |
| `No issues found` | Empty result | Broaden search criteria |

### Issue Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `Issue not found` | Wrong key | Verify format: `ABC-XXX` |
| `Cannot read property` | Issue deleted | Issue may have been removed |
| `Rate limited` | Too many requests | Wait and retry |
| `exceeds maximum allowed tokens` | Issue has too much data | Use `fields` parameter to limit fetched fields |
| `jira_update_issue` parent → silent fail | MCP doesn't set parent on Bug/Story | Use REST API v3: `api._request('PUT', '/rest/api/3/issue/KEY', {'fields': {'parent': {'key': 'EPIC-KEY'}}})` |
| `jira_create_issue` parent → silent fail | MCP may silently ignore parent | Verify after create, use REST API if needed |
| `jira_update_issue(fields=...)` → unexpected kwarg | Wrong parameter name | Use `additional_fields` not `fields` for custom fields |

### MCP Parameter Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `jira_get_agile_boards(project_key_or_id=...)` → unexpected kwarg | Wrong parameter name | Use `project_key` not `project_key_or_id` |
| `jira_get_sprint_issues` limit > 50 → validation error | Limit exceeds max | Max `limit=50` — use pagination with `start_at` for more |

### Assignment Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `jira_update_issue` assignee → silent fail | MCP doesn't set assignee | Use `acli jira workitem assign -k "KEY" -a "email" -y` |
| `acli workitem assign -a ""` → failed to resolve | Empty string not valid | Use `--remove-assignee` flag: `acli jira workitem assign -k "KEY" --remove-assignee -y` |
| `acli jira issue update --assignee` → unknown flag | Wrong command | Use `acli jira workitem assign` not `acli jira issue update` |

### Subtask Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `expected 'key' to be string` / `parent not specified` | Parent format wrong | Use `additional_fields={"parent": {"key": "ABC-XXX"}}` — object, not string |
| Subtask + sprint field → `cannot be associated to a sprint` | Subtasks inherit sprint from parent | Remove sprint field from subtask — inherits automatically |

### Agile API Errors

| Error | Cause | Solution |
| --- | --- | --- |
| MCP `sprint: null` doesn't work | MCP can't remove sprint | Use Agile REST API: `POST /rest/agile/1.0/backlog/issue` + numeric IDs |
| Agile API issue key → 204 but no move | Issue key not accepted | Must use numeric ID from `issue["id"]` |
| Sprint field `{"id": N}` → error | Wrong format for sprint field | `{{SPRINT_FIELD}}` accepts plain number: `{"{{SPRINT_FIELD}}": 123}` |

### Issue Link Errors

| Error | Cause | Solution |
| --- | --- | --- |
| Issue link "Relates to" → error | Wrong link type name | Correct name is `"Relates"` / valid: `Blocks`, `Duplicate`, `Cloners` |

### Parallel MCP Call Errors

| Error | Cause | Solution |
| --- | --- | --- |
| `Sibling tool call errored` | One parallel MCP call failed → all others cancelled | Fix the failing call first; validate JQL before parallel execution |

### Large Output Error

When encountering this error:

```text
Error: result (73,235 characters) exceeds maximum allowed tokens.
Output has been saved to /path/to/tool-results/...
```

**Solution:** Use the `fields` parameter to limit fetched data:

```python
# ❌ Bad - fetches all fields, causing excessive data
jira_get_issue(issue_key="ABC-XXX")

# ✅ Good - specify only the fields you need
jira_get_issue(
    issue_key="ABC-XXX",
    fields="summary,status,description,issuetype,parent",
    comment_limit=5
)
```

**Recommended fields for common operations:**

| Use Case | Fields |
| --- | --- |
| Quick status check | `summary,status,assignee` |
| Read description | `summary,status,description` |
| Check parent/links | `summary,status,issuetype,parent` |
| Full analysis | `summary,status,description,issuetype,parent,labels` |

## Common Workflow Errors

### Phase 1: Discovery

| Issue | Solution |
| --- | --- |
| Can't find parent Epic | Search: `project = {{PROJECT_KEY}} AND type = Epic` |
| Story not found | Verify issue key, check permissions |

### Phase 2: Design

| Issue | Solution |
| --- | --- |
| Generic file paths | **MUST explore codebase first** - use Task(Explore) |
| Wrong service tag | Check tags: `[BE]`, `[FE-Admin]`, `[FE-Web]` |

### Phase 3: Create

| Issue | Solution |
| --- | --- |
| acli create fails | Check JSON format, validate ADF structure |
| Missing parent link | Add `parent` field for sub-tasks |
| Wrong issue type | Use: `Story`, `Sub-task`, `Epic` (exact case) |

### Phase 4: Update

| Issue | Solution |
| --- | --- |
| Edit overwrites content | Always fetch current first, then merge |
| Lost original intent | Compare before/after, preserve core meaning |

## Recovery Procedures

| Scenario | Steps |
| --- | --- |
| Create fails | Check error → validate JSON/ADF → retry → try simpler description |
| Update fails | Re-fetch current state → compare → check concurrent edits → retry |
| Workflow interrupted | Note last completed phase → search Jira for created issue → resume or delete duplicate |

## Validation Commands

```bash
# Validate JSON syntax
cat {{artifacts_dir}}/issue.json | jq .

# Test acli connection
acli jira issue get ABC-1
```

For MCP: Use `jira_get_issue(issue_key: "ABC-1")`

## Confluence & Mermaid Errors

Full Confluence troubleshooting (scripts, MCP limitations, Mermaid, panels, page appearance): see `mermaid-guide.md` and `.claude/rules/mermaid.md`

Quick reference:

| Issue | Solution |
| --- | --- |
| Code blocks not highlighted | `fix_confluence_code_blocks.py --page-id` |
| Macros as text | `update_page_storage.py` |
| Cannot move page | `move_confluence_page.py` |
| Mermaid not rendering | Need code block + Forge `ac:adf-extension` macro (see `mermaid-guide.md`) |
| "Error loading extension!" on panels | `fix_confluence_panels.py --page-id` (ADF panel conversion bug) |
| `401 Unauthorized` (scripts) | Check `~/.config/atlassian/.env` |

## Quick Fixes

| Problem | Quick Fix |
| --- | --- |
| Description ugly format | Use `acli --from-json` not MCP |
| Thai characters broken | Ensure UTF-8 encoding |
| Inline code not rendering | Use `marks: [{"type": "code"}]` |
| Panel wrong color | info (blue), success (green), warning (yellow), error (red) |

## Related

- ADF format: `templates.md` · Tool selection: `tools.md` · Scripts: `../scripts/docs/README.md`
