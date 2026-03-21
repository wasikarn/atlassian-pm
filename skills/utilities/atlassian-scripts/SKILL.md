---
name: atlassian-scripts
description: |
  Python scripts for updating Confluence pages and Jira issues via REST API directly.
  Use when MCP tools have limitations (e.g., code macro formatting, ADF manipulation).

  Triggers: "fix confluence", "update confluence page", "confluence script", "fix jira description", "atlassian script"
argument-hint: "[script-name] [args]"
user-invocable: false
---

# Atlassian Scripts

**Role:** Developer / Tech Lead
**Scripts location:** `scripts/api/` (project root)
**Library:** `scripts/lib/`

> See [../../../scripts/docs/README.md](../../../scripts/docs/README.md) for full architecture, available scripts, and module responsibilities.

---

## Quick Reference

| Script | Use Case |
| --- | --- |
| `update_page_storage.py` | Pages requiring macros (ToC, Children) — HR4 |
| `jira_write.py` | Create subtask: validate → create → verify → assign (HR1/HR3/HR5/HR6) |
| `jira_set_parent.py` | Set/remove parent (Epic) — MCP/acli silently fail |
| `validate_adf.py` | ADF quality gate before create/update (HR1) |
| `verify_write.py` | Verify Jira writes took effect (HR3/HR5/HR6) |
| `create_confluence_page.py` | Create/update pages with proper code blocks |
| `fix_confluence_code_blocks.py` | Fix broken code formatting |
| `audit_confluence_pages.py` | Verify content across multiple pages |
| `update_jira_description.py` | Find/replace in Jira ADF descriptions |

## Usage Pattern

```bash
uv run scripts/api/<script-name>.py [args]
```

## Prerequisites

**Credentials:** `~/.config/atlassian/.env`

```env
CONFLUENCE_URL=https://{{JIRA_SITE}}/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token
```

---

## Examples

### ✅ Good

```text
uv run scripts/api/fix_confluence_code_blocks.py --page-id 123456789
# Fix broken code block rendering after MCP create/update (mandatory post-step for pages with code)

uv run scripts/api/update_page_storage.py --page-id 123456789 --add-toc
# Add Table of Contents macro — MCP cannot render macros (HR4)

uv run scripts/api/jira_set_parent.py --issues BEP-55 --parent BEP-10
# Set epic parent on existing issue — MCP and acli silently fail for this operation

uv run scripts/api/jira_write.py --subtask --parent BEP-42 --summary "[BE] Add endpoint"
# Create subtask with full HR1/HR3/HR5/HR6 compliance built in
```

### ❌ Bad

```text
uv run scripts/api/fix_confluence_code_blocks.py
# Missing --page-id — script has no default; will error immediately

confluence_update_page(page_id=..., content="... {toc} ...")
# Using MCP to add a ToC macro — HR4: MCP HTML-escapes it to raw XML; use update_page_storage.py

uv run scripts/api/update_page_storage.py --page-id 123456789
# Calling update_page_storage.py when MCP works fine — unnecessary complexity;
# only use scripts when MCP has a known limitation (macros, code blocks, parent fields)

uv run scripts/api/fix_confluence_code_blocks.py --page-id 123456789
# Running without ~/.config/atlassian/.env configured — all scripts require API credentials
```

**Common mistakes:**

- Calling `fix_confluence_code_blocks.py` without `--page-id` — the script does not auto-detect the page; always pass the Confluence page ID returned from the create/update step
- Using these scripts when MCP works correctly — scripts are the fallback for MCP limitations (macro rendering, parent fields, code block formatting); default to MCP first
- Running any script without `~/.config/atlassian/.env` set up with `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, and `CONFLUENCE_API_TOKEN` — all scripts will fail with an authentication error
- Using `jira_write.py` for non-subtask issues — this script is purpose-built for subtask creation with HR compliance; use MCP `jira_create_issue` for epics and stories

---

## References

> See [../../../scripts/docs/README.md](../../../scripts/docs/README.md) for full docs, decision tree, and known issues.

- [script-reference.md](../../../scripts/docs/script-reference.md) — Script 1-12 usage, arguments, examples
- [library-api.md](../../../scripts/docs/library-api.md) — ConfluenceAPI, JiraAPI, Converters, Exceptions
- [technical-notes.md](../../../scripts/docs/technical-notes.md) — SSL, Storage Format, Mermaid, History
- Confluence REST API: <https://developer.atlassian.com/cloud/confluence/rest/v1/intro/>
- Jira REST API v3: <https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/>
