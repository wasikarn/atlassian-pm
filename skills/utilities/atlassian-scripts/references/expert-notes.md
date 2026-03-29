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
- **Verification coverage:** `verify_write.py` should confirm 100% of subtask creates — MCP silently ignores parent fields ~15% of the time (observed empirically — not a documented Atlassian behavior; HR5); unverified creates are orphaned in the backlog

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
