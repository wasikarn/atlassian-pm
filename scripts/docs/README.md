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
**Output:** Created/Updated Confluence Pages & Jira Issues
**Version:** 4.0.0 (+ ADF validator, write wrapper, verify, workflow state)

## Architecture

```text
scripts/
├── lib/                     # Shared library modules
│   ├── __init__.py          # Public exports
│   ├── exceptions.py        # Custom exceptions (Confluence + Jira + Validation)
│   ├── auth.py              # SSL, credentials, auth
│   ├── api.py               # ConfluenceAPI class
│   ├── jira_api.py          # JiraAPI class (REST v3, ADF)
│   ├── converters.py        # Content converters
│   ├── adf_validator.py     # ADF quality gate engine (HR1)
│   └── workflow_state.py    # Workflow state + prerequisites
├── api/                     # CLI scripts
│   ├── create_confluence_page.py
│   ├── update_confluence_page.py
│   ├── move_confluence_page.py
│   ├── update_page_storage.py
│   ├── fix_confluence_code_blocks.py
│   ├── audit_confluence_pages.py
│   ├── update_jira_description.py
│   ├── validate_adf.py          # Script 8: ADF validator (HR1)
│   ├── verify_write.py          # Script 9: Post-write verifier (HR3/HR5/HR6)
│   ├── jira_write.py            # Script 10: Write wrapper (HR1/HR3/HR5/HR6)
│   ├── workflow_checkpoint.py   # Script 11: Workflow state CLI
│   └── jira_set_parent.py       # Script 12: Set parent (Epic) via REST
├── sprint/                  # Sprint management scripts
└── analysis/                # Analysis tools (AC mapper, impact suggester, QA matrix)
```

### Module Responsibilities (SRP)

| Module | Responsibility |
| --- | --- |
| `exceptions.py` | Domain-specific exceptions (Confluence + Jira + Validation) |
| `auth.py` | Authentication (SSL, credentials, auth header) |
| `api.py` | HTTP/API operations via ConfluenceAPI class |
| `jira_api.py` | Jira REST API v3 client (ADF manipulation) |
| `converters.py` | Content transformation (markdown, code blocks) |
| `adf_validator.py` | ADF quality gate engine — 25+ checks, scoring, auto-fix (HR1) |
| `workflow_state.py` | Workflow state management — phase tracking, prerequisites |

---

## Available Scripts

| Script | Description | Use Case |
| --- | --- | --- |
| `create_confluence_page.py` | Create/Update page with proper code blocks | Create or update pages containing code |
| `update_confluence_page.py` | Find/Replace text in a page | Batch text replacement |
| `move_confluence_page.py` | Move page(s) to new parent | Reorganize page hierarchy |
| `update_page_storage.py` | Update page with raw storage format | Pages requiring macros (ToC, Children) |
| `fix_confluence_code_blocks.py` | Fix code blocks that render incorrectly | Fix broken code formatting |
| `audit_confluence_pages.py` | Verify content across multiple pages | Alignment verification |
| `update_jira_description.py` | Find/Replace text in Jira ADF descriptions | Fix Jira issue descriptions |
| `validate_adf.py` | Validate ADF JSON against quality gate (HR1) | Before creating/updating issues |
| `verify_write.py` | Verify Jira writes took effect (HR3/HR5/HR6) | After creating subtasks, assigning |
| `jira_write.py` | Write wrapper: validate → create → verify → assign | Create subtask, update description |
| `workflow_checkpoint.py` | Track workflow phases + prerequisite enforcement | Multi-step skill workflows |
| `jira_set_parent.py` | Set/remove parent (Epic) on existing issues | MCP/acli silently fail on parent field |

---

## Prerequisites

**Credentials:** `~/.config/atlassian/.env`

```env
CONFLUENCE_URL=https://{{JIRA_SITE}}/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token
```

---

## Script Selection Guide

> See [references/script-selection-guide.md](references/script-selection-guide.md) for a decision tree on which script to use.

---

## When to Use Scripts vs MCP

> See [references/when-to-use.md](references/when-to-use.md) for MCP vs script decision rules and known issues.

---

## Supporting Files

> Load only when needed -- no need to load everything on invoke.

| File | Content | Load When |
| --- | --- | --- |
| [script-reference.md](script-reference.md) | Script 1-11 usage, arguments, examples | After selecting a script, when you need full docs |
| [library-api.md](library-api.md) | ConfluenceAPI, JiraAPI, Converters, Exceptions | When creating a custom script |
| [technical-notes.md](technical-notes.md) | SSL, Storage Format, Mermaid, History | Troubleshooting |

---

## References

- [references/script-selection-guide.md](references/script-selection-guide.md) — decision tree for script selection
- [references/when-to-use.md](references/when-to-use.md) — MCP vs script decision rules and known issues
- Confluence REST API: <https://developer.atlassian.com/cloud/confluence/rest/v1/intro/>
- Jira REST API v3: <https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/>
- Credentials: `~/.config/atlassian/.env`
- Storage Format: <https://developer.atlassian.com/cloud/confluence/confluence-storage-format/>
- ADF (Atlassian Document Format): <https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/>
