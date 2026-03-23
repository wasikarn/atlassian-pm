---
paths:
  - "skills/**"
  - "hooks/**"
  - "scripts/**"
---

## Tool Selection

| Operation | Tool | Notes |
| --- | --- | --- |
| Description (full replace) | `acli --from-json` (ADF JSON) | Fields only: MCP `jira_update_issue` · **NEVER use MCP for find/replace** |
| Description (find/replace) | `update_jira_description.py` (REST) | ADF-safe · preserves panels/tables/code blocks · supports batch + dry-run |
| Read issue | `cache_get_issue` → `jira_get_issue` | Always use `fields` param |
| Search | `cache_search` / `cache_text_search` → `jira_search` | Always use `fields` + `limit` |
| Comment | MCP `jira_add_comment` | |
| Sub-task | Two-Step: MCP create → acli edit | `parent` doesn't work with acli |
| Script | `update_jira_description.py` (REST) | `/atlassian-pm:atlassian-scripts` for format |
| Confluence | MCP (read/simple), Python scripts (code/macros) | `audit_confluence_pages.py` (audit) |
| Confluence (advanced) | See `troubleshooting.md` + `mermaid-guide.md` | Page appearance, Mermaid, ADF panels |
| Explore | Task(Explore) | Always before creating subtasks |
| Parent (Epic) | `jira_set_parent.py` (REST) | MCP/acli silently ignore parent field on existing issues |
| Issue Links | MCP `jira_create_issue_link` | Blocks/Relates · `jira_create_remote_issue_link` (web) |
| Sprint | Agile REST via `JiraAPI._request()` | MCP can't move to backlog |
| Sprint batch | `scripts/sprint/` | `clear_sprint_dates.py`, `sprint_set_fields.py`, `sprint_rank_by_date.py`, `sprint_subtask_alignment.py`, `update_sprint_goals.py` |
| Cache | MCP `atlassian-cache` (8 tools) | `force_refresh=true` after web edits or "ล่าสุด/refresh/stale" |

### Field & ADF Quick Reference

**`jira_get_issue`** — always use `fields` param · **`jira_search`** — always use `fields` + `limit` params → see `skills/shared-references/tools.md` for preset tables

**ADF CREATE vs EDIT differ** — CREATE: `projectKey`+`type`+`summary`+`description` (no `issues`) · EDIT: `issues`+`description` (no `projectKey`/`type`/`summary`/`parent`) → details in `skills/shared-references/templates-core.md`
**Subtask Two-Step:** MCP create (with `parent:{key:"ABC-XXX"}`) → acli `workitem edit --from-json`
**Smart Link:** see `skills/shared-references/templates-core.md` for inlineCard format
