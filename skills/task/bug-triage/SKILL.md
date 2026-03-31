---
name: bug-triage
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Structured bug triage workflow for QA: intake → severity scoring → duplicate check → assign → create Jira Task.
  Distinct from /create-task bug (which is just ticket creation). This skill is a full triage workflow.
  Triggers: "bug triage", "triage bug", "report bug", "new bug", "bug found", "จัดการ bug", "รายงาน bug"
  Use when: triaging an incoming bug report — severity scoring, dedup check, assignment, and Jira creation
  Do NOT use for: creating a simple task (use create-task); creating a story (use create-story)
argument-hint: "[--no-assign] [description]"
effort: medium
---

# /bug-triage

**Role:** QA — Bug Triage Lead
**Output:** Jira Task (Bug) with severity label + assignee + structured repro steps

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`

## Context Object

| Phase | Adds to Context |
| --- | --- |
| 1. Intake | `bug_summary`, `repro_steps[]`, `environment`, `observed`, `expected` |
| 2. Severity | `severity` (P1/P2/P3), `severity_rationale` |
| 3. Duplicate Check | `duplicate_found: bool`, `duplicate_key` (if found) |
| 4. Assign | `assignee_email` |
| 5. Create | `issue_key` |
| 6. Summary | Done |

## Phase 1 — Bug Intake ⛔ GATE

If description provided as argument: use as `bug_summary`, ask for remaining fields.

Collect: Summary · Reproduction Steps (numbered) · Environment (service+version+env) · Observed Behavior · Expected Behavior · Affected User · Frequency · Attachments (optional)

Display collected intake as a `## Bug Report` block with all fields, then confirm before scoring.

## Phase 2 — Severity Scoring 🟡 REVIEW

| Severity | Criteria | Response Time |
| --- | --- | --- |
| **P1 — Critical** | Data loss · security breach · system down · payment failure · all users blocked | Immediate |
| **P2 — Major** | Key feature broken · significant UX degradation · partial data issue · majority affected | Next sprint |
| **P3 — Minor** | Cosmetic · edge case · workaround exists · rare frequency | Backlog |

Display `## Severity Assessment` with P1/P2/P3, rationale, and response time. Auto-proceed unless user objects.

## Phase 3 — Duplicate Check 🟢 AUTO

1. `cache_search(query="[bug_summary]", limit=5)`
2. `jira_search(jql="project = {{PROJECT_KEY}} AND issuetype = Task AND text ~ '[keywords]'", fields="summary,status,assignee")`

If duplicate found: show key, summary, status, link — offer (1) link to existing or (2) create separate. If none found: auto-proceed silently.

## Phase 4 — Assign ⛔ GATE

> **Skip if `--no-assign`** — proceed directly to Phase 5 with `assignee_email = null`.

Recommend assignee based on affected service tag and team skill matrix. Show `## Assignment Recommendation` with recommended + fallback. Wait for user confirmation. Record `assignee_email` from `team.members[]`.

## Phase 5 — Create Jira Task 🟢 AUTO

**Summary format:** `[Bug][P1/P2/P3] [bug_summary]`

**ADF structure** (use `templates-task.md` bug template): Bug Description (error panel) · Reproduction Steps (numbered) · Expected vs Actual (table) · Environment (note panel) · Affected Users · Attachments · Fix Criteria (success panel)

**Quality Gate** — T1–T5 + bug-specific:

| Check | Criterion |
| --- | --- |
| B1 | Summary includes severity label [P1/P2/P3] |
| B2 | Reproduction steps are numbered and specific |
| B3 | Expected vs Actual is explicit (not combined) |
| B4 | Environment field is filled |
| B5 | Fix criteria are testable and specific |

QG ≥ 90% before creation. HR1 enforced.

> **🟢 AUTO (validate_adf.py):** `uv run scripts/api/validate_adf.py {{artifacts_dir}}/tp-xxx-bug.json --type task --json` — score ≥ 90 = PASS; if FAIL → apply `--fix` → re-score (max 1 cycle).

```bash
acli jira workitem create --from-json {{artifacts_dir}}/tp-xxx-bug.json
# HR3: assign via acli (MCP assignee silently fails)
acli jira workitem assign -k "[issue_key]" -a "[assignee_email]" -y
```

`jira_update_issue(issue_key="[issue_key]", additional_fields={"labels": ["P1"|"P2"|"P3"]})`

> **HR6:** `cache_invalidate(issue_key)` after each write.

## Phase 6 — Summary

```
## ✅ Bug Triaged: [KEY]

**Severity:** [P1/P2/P3] — [label]
**Assignee:** [name]
**Status:** To Do

🔗 [View in Jira](https://{{JIRA_SITE}}/browse/[KEY])

→ Use /verify-issue [KEY] to re-check quality
→ Add comments with new repro evidence as investigation continues
→ Use /create-testplan [KEY] to create QA verification subtask after fix
```

## References

[ADF Core Rules](../../../references/templates-core.md) · [Task Template](../../../references/templates-task.md) · [Verification Checklist](../../../references/verification-checklist.md) · [Tools Reference](../../../references/tools.md) · [Scenarios](references/scenarios.md)

After: `/verify-issue [KEY]` · `/create-testplan [KEY]`

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
