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
**Scripts location:** `atlassian-scripts/scripts/` (project root)
**Library:** `atlassian-scripts/lib/`

> See [../../../atlassian-scripts/README.md](../../../atlassian-scripts/README.md) for full architecture, available scripts, and module responsibilities.

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
cd atlassian-scripts
uv run scripts/<script-name>.py [args]
```

## Prerequisites

**Credentials:** `~/.config/atlassian/.env`

```env
CONFLUENCE_URL=https://{{JIRA_SITE}}/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token
```

---

## References

> See [../../../atlassian-scripts/README.md](../../../atlassian-scripts/README.md) for full docs, decision tree, and known issues.

- [script-reference.md](../../../atlassian-scripts/script-reference.md) — Script 1-12 usage, arguments, examples
- [library-api.md](../../../atlassian-scripts/library-api.md) — ConfluenceAPI, JiraAPI, Converters, Exceptions
- [technical-notes.md](../../../atlassian-scripts/technical-notes.md) — SSL, Storage Format, Mermaid, History
- Confluence REST API: <https://developer.atlassian.com/cloud/confluence/rest/v1/intro/>
- Jira REST API v3: <https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/>
