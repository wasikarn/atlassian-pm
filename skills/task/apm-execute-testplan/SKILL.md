---
name: apm-execute-testplan
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
  This skill should be used when QA wants to automate execution of a Google Sheet test plan linked to a Jira story. Uses Playwright for browser automation, writes results back to the sheet, and creates bug tickets for failures.
  
  Trigger phrases: "execute testplan", "run test", "execute test cases", "run QA", "ทดสอบ", "รัน testplan"
  
  This skill should NOT be used for creating new test plans (use create-testplan), unit/API-only tests, or stories with no Sheet link and no ACs.
argument-hint: "<issue-key> [--env staging|production] [--headed] [--rerun-failed] [--dry-run]"
effort: high
---

# /atlassian-pm:apm-execute-testplan

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

Read from `.claude/project-config.json` → `environments.<env>`.

## Test Type Strategy

| Test Type | Mode |
| --- | --- |
| Positive / Negative / Edge | headless |
| OAuth popup, LINE connect | headed |
| `--headed` flag | headed (override all) |

Auto-detect headed: if Description or Test Steps contains `OAuth`, `popup`, `LINE connect`, `เชื่อมต่อ LINE`, `authorization` → switch to headed.

## Google Sheet Column Map

| Col | Field | R/W |
| --- | --- | --- |
| A–H | Test ID, Feature, Description, Type, Precondition, Data, Steps, Expected | Read |
| I | Actual Result | Write |
| J | Status (`pass`/`fail`/`skip`/`blocked`) | Write |
| K | Date | Write |
| L | Remark (append bug key if fail) | Write |

Metadata rows (read only): Row 1=Project, 2=Story Name, 3=Create By, 4=Assignee, 5=Figma. Header: Row 7. Data: Row 8+.

## Context Object

| Phase | Adds |
| --- | --- |
| 1 | `issue`, `sheet_url`, `remote_links` |
| 2 | `test_cases[]`, `metadata` |
| 3 | `env_url`, `headed_tests[]`, `estimated_time` |
| 4 | `results[]` (actual, status, screenshot_path, console_errors) |
| 5 | `sheet_updated: true` |
| 6 | `bugs_created[]`, `summary` |

## Phase 1 — Issue & Sheet Discovery

> **🟢 PARALLEL** — Steps 1 and 2 run simultaneously.

1. `jira_get_issue(issue_key, fields="summary,description,status,labels,issuelinks")` → extract ACs, summary, labels, linked bugs
2. `acli jira weblink list -k "<issue_key>" -y` → find `docs.google.com` / `drive.google.com` URL

If Sheet not found → offer: [A] paste URL manually · [B] generate from ACs + create Sheet · [C] abort. Wait for choice.

## Phase 2 — Sheet Parse

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 2: Sheet Parse Script**

## Phase 3 — Pre-flight Check

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 3: Pre-flight Check Script**

## Phase 4 — Execute Tests

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 4: Execute Tests Script**

## Phase 5 — Update Google Sheet

1. `browser_navigate(url=sheet_url)` — ensure sheet is editable
2. For each result: locate row by Test ID (col A) → write I (actual), J (status), K (date DD/MM/YYYY), L (bug key if fail)
   - Colors: pass=#b7e1cd · fail=#f4c7c3 · skip=#efefef · blocked=#fce8b2
3. Verify saved (spinner/Saving… disappears)
4. If view-only → warn + export results as markdown table in Jira comment

## Phase 6 — Bug Triage & Summary

See [references/phase-scripts.md](references/phase-scripts.md) — **Phase 6: Bug Triage & Summary Script**

## Examples

### ✅ Good

```text
/execute-testplan {{PROJECT_KEY}}-42                           # run test plan for {{PROJECT_KEY}}-42 on staging
/execute-testplan {{PROJECT_KEY}}-42 --env production          # run against production
/execute-testplan {{PROJECT_KEY}}-42 --headed                   # force visible browser for all tests
/execute-testplan {{PROJECT_KEY}}-42 --rerun-failed            # retry only failed tests
/execute-testplan {{PROJECT_KEY}}-42 --dry-run                  # parse sheet, show plan, don't execute
```

### ❌ Bad

```text
/execute-testplan                                 # no issue key — cannot find sheet
/execute-testplan {{PROJECT_KEY}}-42 --sprint                  # --sprint is not valid; test plans are per-story
/execute-testplan {{PROJECT_KEY}}-42 --browser chrome          # browser selection is not supported; Playwright uses chromium
```

**Common mistakes:**

- Running without linked Sheet — test plan must have a Google Sheet weblink on the Jira story
- Skipping headed mode for OAuth tests — OAuth popups require headed browser; auto-detected but can force with `--headed`
- Running `--rerun-failed` on first pass — there's no failed status yet; run full test first

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[tools.md](../../../references/tools.md) · [hr-rules.md](../../../references/hr-rules.md) · [jql-quick-ref.md](../../../references/jql-quick-ref.md) · [verification-checklist.md](../../../references/verification-checklist.md)
