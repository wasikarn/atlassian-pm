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

uv run scripts/api/jira_set_parent.py --issues {{PROJECT_KEY}}-55 --parent {{PROJECT_KEY}}-10
# Set epic parent on existing issue — MCP and acli silently fail for this operation

uv run scripts/api/jira_write.py --subtask --parent {{PROJECT_KEY}}-42 --summary "[BE] Add endpoint"
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

---

## 🎓 Domain Expert Notes

### Why This Approach

Direct REST API scripts exist because MCP tool abstractions trade off completeness for safety — they HTML-escape content, silently drop unsupported fields, and lack transactional guarantees. Python scripts fill the gap by calling the same underlying API with full control over request bodies, enabling the validate → create → verify pattern required for idempotent automation.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Idempotency-first design | `jira_write.py` create+verify loop | Atlassian Cloud enforces points-based rate limits (effective March 2026); every write costs 1 point — verify-before-retry prevents duplicate resource creation under transient failures |
| Exponential backoff + jitter | All scripts on HTTP 429/5xx | Atlassian recommends exponential retry with random jitter to avoid thundering herd when multiple automation scripts share the same OAuth token quota |
| ETag conditional requests | `audit_confluence_pages.py` | Cache stable responses using ETags to avoid re-fetching unchanged pages — reduces points consumed per audit run |

### Key Metrics

- **Rate limit budget:** Atlassian Cloud points-based quota — write operations cost 1 point each; scripts creating 50 issues in a loop consume 50 points from the daily quota. Batch where possible.
- **Retry-After compliance:** HTTP 429 responses include a `Retry-After` header — scripts must honour it exactly; ignoring it and retrying immediately causes quota exhaustion and escalating ban windows
- **Verification coverage:** `verify_write.py` should confirm 100% of subtask creates — MCP silently ignores parent fields ~15% of the time (HR5); unverified creates are orphaned in the backlog

### Expert Decision Criteria

- If an HTTP 5xx is returned without a `Retry-After` header → do not retry; treat as a non-transient error and surface it — only retry when the response explicitly signals recoverability
- If creating more than 10 issues in one script run → use `jira_batch_create_issues` MCP endpoint or add 200ms sleep between writes to stay within burst limits
- If `update_page_storage.py` is being called for simple text-only pages → stop and use MCP `confluence_update_page`; scripts add operational overhead and should only be used when MCP macro/code-block limitations apply (HR4)
- If credentials are stored outside `~/.config/atlassian/.env` → reject; never hardcode API tokens in script arguments or environment variables that appear in shell history

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Script exits with 401 Unauthorized | `.env` file missing or token expired | Re-generate API token at `id.atlassian.com` → update `~/.config/atlassian/.env` |
| `jira_write.py` creates subtask but parent is null | MCP `create_issue` silently dropped the `parent` field (HR5) | `verify_write.py` catches this — follow up with `jira_set_parent.py` to re-attach |
| `update_page_storage.py` produces garbled macro XML | Confluence Storage Format macros passed as HTML | Macros must use Storage Format (`<ac:structured-macro>` tags), not HTML `<div>` equivalents |
| HTTP 429 after bulk create script | Rate limit quota exhausted | Add `time.sleep(0.2)` between writes; switch to `jira_batch_create_issues` for bulk operations |
| `fix_confluence_code_blocks.py` runs but page looks unchanged | Wrong `--page-id` (page ID vs. page title passed) | Use numeric Confluence page ID from URL, not the page title string |

### Authoritative References

- **Atlassian Developer Docs (2026):** Points-based rate limiting enforced March 2, 2026 — all Forge, Connect, and OAuth 2.0 apps subject to tiered quotas; write operations = 1 point each
- **Atlassian API Rate Limit Handling Guide:** "Implement retry logic that backs off exponentially rather than retrying immediately, and add random jitter to avoid the thundering herd problem"
- **Atlassian REST API v3 intro:** Field filtering (`fields=summary,status`) and pagination reduce points consumed per read — always specify only required fields in `jira_search` calls
