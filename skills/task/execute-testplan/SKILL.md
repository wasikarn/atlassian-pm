---
name: execute-testplan
disable-model-invocation: true
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

---

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

---

## Phase 2 — Sheet Parse

**Goal:** Read all test cases from the Google Sheet.
**Required inputs:** `sheet_url`
**Constraints:** Sheet must be publicly accessible or user must be logged in to Google in the browser session.
**Output:** `test_cases[]`, `metadata`

```text
1. browser_navigate(url=sheet_url)
   → Wait for sheet to load (wait_for selector: "table" or ".waffle")

2. browser_snapshot()
   → Extract metadata from rows 1–6:
     - Project name (row 1, col C)
     - Story name (row 2, col C)
     - Create By (row 3, col C), Assignee (row 4, col C)

3. browser_evaluate() — extract all rows as JSON:
   const rows = Array.from(document.querySelectorAll('tbody tr'))
     .slice(1) // skip header row
     .map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim()))
   → Parse into test_cases[]:
     { test_id, feature, description, test_type, precondition, test_data, steps, expected, current_status }

4. Apply --rerun-failed filter if flag set:
   → Keep only rows where current_status is empty, "fail", or "blocked"

5. Classify each test case:
   → headed_required: true if steps/description contain OAuth/popup keywords
   → estimated_seconds: Positive=30, Negative=20, Edge=25, OAuth=manual

6. Report to user:
   Total: X test cases (Y headless, Z headed, W manual/OAuth)
   Estimated time: ~N minutes
   Filtered by --rerun-failed: X cases
```

---

## Phase 3 — Pre-flight Check

**Goal:** Verify environment is reachable and confirm execution with user.
**Required inputs:** `env_url`, `test_cases[]`
**Output:** User confirmation, `env_reachable: bool`

```text
1. browser_navigate(url="https://<env_url>")
   → Check HTTP 200 / page loads
   → If unreachable: warn user, ask to continue or abort

2. Display execution plan:
   ┌─────────────────────────────────────────────────┐
   │  Execute Test Plan: <issue_key>                 │
   │  Story: <summary>                               │
   │  Environment: <env> (https://<env_url>)         │
   │  Test cases: X total                            │
   │    Headless:  Y cases                           │
   │    Headed:    Z cases (OAuth/popup)             │
   │    Skip (manual): W cases                       │
   │  Estimated time: ~N minutes                     │
   │  --dry-run: <yes/no>                            │
   └─────────────────────────────────────────────────┘
   Proceed? [Y/n]

3. If --dry-run: print full test case list and EXIT (no execution)

4. Wait for user confirmation before Phase 4
```

---

## Phase 4 — Execute Tests

**Goal:** Run each test case with Playwright; collect results and evidence.
**Required inputs:** `test_cases[]`, `env_url`, user confirmation
**Constraints:** OAuth/popup tests → use headed; capture screenshot on every result.
**Output:** `results[]`

```text
For each test_case in test_cases:

  A. Setup
     - browser_navigate(url="https://<env_url>/<relevant_path>")
     - Apply precondition (login if required — use test account from config or env vars)

  B. Execute steps
     - Parse test_case.steps into Playwright actions:
       "ไปที่หน้า X" → browser_navigate
       "กดปุ่ม X" → browser_click
       "กรอก X" → browser_type / browser_fill_form
       "ตรวจสอบ X ปรากฏ" → browser_snapshot → check element text
       "เลือก X" → browser_select_option
     - browser_console_messages() → capture JS errors
     - browser_network_requests() → capture failed API calls (4xx/5xx)

  C. Evaluate result
     - Compare actual DOM state vs test_case.expected
     - Determine: pass / fail / skip / blocked
       blocked: precondition not met (e.g., OAuth test without real LINE account)

  D. Collect evidence
     - browser_take_screenshot() → save as <test_id>_<status>.png
     - Record: actual_result (text description), console_errors, failed_requests

  E. Record in results[]:
     { test_id, status, actual_result, screenshot_path, console_errors, duration_ms }

  F. Headed test (OAuth/popup):
     - Switch browser to headed mode
     - Navigate to OAuth step
     - Pause: "⚠️ Manual step required: complete LINE authorization in browser window"
     - Wait for user signal (Enter) to continue
     - Resume and evaluate result

Progress display after each test:
  [LN-006] LINE Connect (OAuth) ........... ✅ pass (2.3s)
  [LN-009] Negative — OAuth cancel ........ ❌ fail (1.8s) → screenshot saved
```

---

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

---

## Phase 6 — Bug Triage & Summary

**Goal:** Create Jira bug tickets for failed tests, dedup against existing bugs, post summary comment.
**Required inputs:** `results[]` where status = fail, `issue_key`
**Output:** `bugs_created[]`, summary comment on story

```text
1. Group failures:
   - Group by Feature/Module (column B) — related failures likely 1 bug
   - Group by root cause if multiple tests fail on same step

2. For each failure group:
   a. jira_search(jql: 'project=TP AND issuetype=Bug AND text~"<description>" AND status != Done')
      → Check for duplicate open bug (confidence: EXACT/HIGH/MEDIUM/LOW)

   b. If duplicate found (HIGH/EXACT):
      → jira_add_comment(existing_bug_key, "พบซ้ำใน test run <date>: <test_id> — <actual_result>")
      → Link only (no new ticket)

   c. If no duplicate → create new bug:
      Summary: "[FE-Web/BE] <feature> — <short description> (from <issue_key> test run)"
      Description (ADF):
        ## Steps to Reproduce
        (from test_case.steps)
        ## Expected Result
        (from test_case.expected)
        ## Actual Result
        (from result.actual_result)
        ## Evidence
        Screenshot: <screenshot_path>
        Console errors: <if any>
        Failed requests: <if any>
        ## Test Case
        Test ID: <test_id> | Type: <test_type>
      Priority: Positive fail = High, Negative/Edge fail = Medium
      Labels: ["qa-automation", "<label from story>"]
      → jira_create_issue(...)
      → jira_create_issue_link(type="Relates", inward=new_bug, outward=issue_key)

3. Post execution summary comment on issue_key:
   ## 🧪 Test Execution Summary
   **Story:** <issue_key> — <summary>
   **Environment:** <env> | **Date:** <date> | **Tester:** Claude (automated)

   | Result | Count |
   |--------|-------|
   | ✅ Pass | X |
   | ❌ Fail | Y |
   | ⏭ Skip | Z |
   | 🚫 Blocked | W |
   | **Total** | **N** |

   **Bugs created:** {{PROJECT_KEY}}-XXXX, TP-YYYY
   **Sheet:** <sheet_url>

4. Print final report to user
```

---

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

- `../../../references/tools.md` — Jira field presets, create_issue payload
- `../../../references/hr-rules.md` — HR2 JQL, HR5 subtask parent, HR6 cache invalidate
- `../../../references/jql-quick-ref.md` — Bug dedup JQL patterns
- `../../../references/verification-checklist.md` — AC coverage verification
