# Phase Scripts — /execute-testplan

Pseudocode and step sequences for each execution phase. Referenced from SKILL.md.

---

## Phase 2 — Sheet Parse Script

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

## Phase 3 — Pre-flight Check Script

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

## Phase 4 — Execute Tests Script

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

## Phase 6 — Bug Triage & Summary Script

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
