---
name: execute-testplan
context: fork
agent: general-purpose
x-compatibility: [mcp-atlassian, playwright]
allowed-tools: >
  Bash, Read, Write, TodoWrite,
  mcp__mcp-atlassian__jira_get_issue,
  mcp__mcp-atlassian__jira_add_comment,
  mcp__mcp-atlassian__jira_create_issue,
  mcp__mcp-atlassian__jira_search,
  mcp__plugin_playwright_playwright__browser_navigate,
  mcp__plugin_playwright_playwright__browser_snapshot,
  mcp__plugin_playwright_playwright__browser_click,
  mcp__plugin_playwright_playwright__browser_type,
  mcp__plugin_playwright_playwright__browser_fill_form,
  mcp__plugin_playwright_playwright__browser_take_screenshot,
  mcp__plugin_playwright_playwright__browser_wait_for,
  mcp__plugin_playwright_playwright__browser_evaluate,
  mcp__plugin_playwright_playwright__browser_select_option,
  mcp__plugin_playwright_playwright__browser_press_key,
  mcp__plugin_playwright_playwright__browser_close,
  mcp__plugin_playwright_playwright__browser_console_messages,
  mcp__plugin_playwright_playwright__browser_network_requests
description: |
  Execute test cases from a Google Sheet linked to a Jira story using Playwright, then write results back and create bug tickets.

  Triggers:
  - "execute testplan {{PROJECT_KEY}}-XXX", "run test {{PROJECT_KEY}}-XXX"
  - "รัน testplan", "ทดสอบ {{PROJECT_KEY}}-XXX", "execute test cases"
  - "run QA", "QA run"

  Use when: QA wants to automate execution of a Google Sheet test plan linked to a Jira story and record results.
  Do NOT use for: creating new test plans (use create-testplan); unit/API-only tests; stories with no Sheet link and no ACs.
argument-hint: "<issue-key> [--env staging|production] [--headed] [--rerun-failed] [--dry-run]"
effort: high
---

# /execute-testplan

**Role:** Senior QA Automation Engineer
**Output:** Sheet results updated (I/J/K), Jira bug tickets for failures, execution summary comment on story

## Flags

| Flag | Default | Description |
| --- | --- | --- |
| `--env staging\|production` | staging | Target environment |
| `--headed` | false | Force headed (visible browser) for all tests |
| `--rerun-failed` | false | Run only tests with Status = fail or empty |
| `--dry-run` | false | Parse sheet + show plan, do not execute |

## Environment URLs

Read from `.claude/project-config.json` → `environments.<env>`:

- staging web: read from `environments.staging.web`
- production web: read from `environments.production.web`

## Test Type Strategy

| Test Type | Mode | Notes |
| --- | --- | --- |
| Positive | headless | Standard flow |
| Negative | headless | Error/validation paths |
| Edge | headless | Boundary conditions |
| Any with OAuth popup, LINE connect | **headed** | Third-party popup requires visible browser |
| Any with `--headed` flag | headed | Override all |

Auto-detect headed requirement: if Description or Test Steps contains keywords `OAuth`, `popup`, `LINE connect`, `เชื่อมต่อ LINE`, `authorization` → switch to headed.

## Google Sheet Column Map

| Col | Field | Read/Write |
| --- | --- | --- |
| A | Test ID | Read |
| B | Feature / Module | Read |
| C | Description | Read |
| D | Test Type | Read |
| E | Precondition | Read |
| F | Test Data | Read |
| G | Test Steps | Read |
| H | Expected Result | Read |
| I | Actual Result | **Write** |
| J | Status (`pass`/`fail`/`skip`/`blocked`) | **Write** |
| K | Date | **Write** |
| L | Remark | **Write** (append bug key if fail) |

Metadata rows (read only): Row 1 = Project, Row 2 = Story Name, Row 3 = Create By, Row 4 = Assignee, Row 5 = Figma link.
Header row: Row 7. Test data starts: Row 8.

## Context Object

| Phase | Adds to Context |
| --- | --- |
| 1 | `issue` (ACs, summary), `sheet_url`, `remote_links` |
| 2 | `test_cases[]` (all rows parsed), `metadata` |
| 3 | `env_url`, `headed_tests[]`, `estimated_time` |
| 4 | `results[]` (per test: actual, status, screenshot_path, console_errors) |
| 5 | `sheet_updated: true` |
| 6 | `bugs_created[]`, `summary` |

## Phase 1 — Issue & Sheet Discovery

**Goal:** Fetch Jira issue context and locate the Google Sheet test plan.
**Required inputs:** `issue_key`
**Output:** `issue`, `sheet_url` (or fallback flag)

```text
1. jira_get_issue(issue_key, fields="summary,description,status,labels,issuelinks")
   → Extract: ACs, story summary, labels, linked bugs

2. Fetch remote/web links via Bash:
   acli jira weblink list -k "<issue_key>" -y
   → Search for Google Drive/Sheets URL (icon or URL contains "docs.google.com" or "drive.google.com")

3. If Sheet URL found → set sheet_url, proceed to Phase 2
   If NOT found:
   → Warn: "ไม่พบ Google Sheet ใน Web links ของ <issue_key>"
   → Offer options:
     [A] Paste Sheet URL manually
     [B] Generate test cases from ACs and create new Sheet (requires Google auth)
     [C] Abort
   → Wait for user choice before proceeding
```

> **🟢 PARALLEL** — Steps 1 and 2 can run simultaneously.

## Phase 2 — Sheet Parse

**Goal:** Read all test cases from the Google Sheet.
**Required inputs:** `sheet_url`
**Constraints:** Sheet must be publicly accessible or user must be logged in to Google in the browser session.
**Output:** `test_cases[]`, `metadata`

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 2: Sheet Parse Script**

## Phase 3 — Pre-flight Check

**Goal:** Verify environment is reachable and confirm execution with user.
**Required inputs:** `env_url`, `test_cases[]`
**Output:** User confirmation, `env_reachable: bool`

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 3: Pre-flight Check Script**

## Phase 4 — Execute Tests

**Goal:** Run each test case with Playwright; collect results and evidence.
**Required inputs:** `test_cases[]`, `env_url`, user confirmation
**Constraints:** OAuth/popup tests → use headed; capture screenshot on every result.
**Output:** `results[]`

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 4: Execute Tests Script**

## Phase 5 — Update Google Sheet

**Goal:** Write execution results back to the Google Sheet (columns I, J, K, L).
**Required inputs:** `results[]`, `sheet_url`
**Output:** `sheet_updated: true`

```text
1. browser_navigate(url=sheet_url)
   → Ensure sheet is loaded and editable

2. For each result in results[]:
   a. Locate the row by Test ID (column A match)
   b. Click cell I (Actual Result) → type actual_result text
   c. Click cell J (Status) → type status ("pass" / "fail" / "skip" / "blocked")
      → Apply background color via Apps Script or cell formatting:
        pass = green (#b7e1cd), fail = red (#f4c7c3), skip = grey (#efefef), blocked = orange (#fce8b2)
   d. Click cell K (Date) → type today's date (DD/MM/YYYY)
   e. Click cell L (Remark) → append bug key if fail (e.g., "{{PROJECT_KEY}}-XXXX")

3. Verify changes saved (check spinner / "Saving..." text disappears)

4. Report: "✅ Updated X rows in Sheet"

Note: If Google Sheet is not editable (view-only link):
→ Warn user + export results as markdown table in Jira comment instead
```

## Phase 6 — Bug Triage & Summary

**Goal:** Create Jira bug tickets for failed tests, dedup against existing bugs, post summary comment.
**Required inputs:** `results[]` where status = fail, `issue_key`
**Output:** `bugs_created[]`, summary comment on story

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 6: Bug Triage & Summary Script**

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[tools.md](../../../references/tools.md) · [hr-rules.md](../../../references/hr-rules.md) · [jql-quick-ref.md](../../../references/jql-quick-ref.md) · [verification-checklist.md](../../../references/verification-checklist.md)
