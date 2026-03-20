---
name: bug-triage
disable-model-invocation: true
x-compatibility: [jira-cache-server, mcp-atlassian, acli]
description: |
  Structured bug triage workflow for QA: intake → severity scoring → duplicate check → assign → create Jira Task.
  Distinct from /create-task bug (which is just ticket creation). This skill is a full triage workflow.
  Triggers: "bug triage", "triage bug", "report bug", "new bug", "bug found", "จัดการ bug", "รายงาน bug"
argument-hint: "[description]"
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

---

## Phase 1 — Bug Intake ⛔ GATE

Collect all required information before proceeding.

**If description provided as argument:** use it as `bug_summary` and ask for remaining fields.

**Collect:**

| Field | Question |
| --- | --- |
| Summary | One-line description of the bug |
| Reproduction Steps | Step-by-step to reproduce (numbered list) |
| Environment | Service + version + environment (staging/production) |
| Observed Behavior | What actually happens |
| Expected Behavior | What should happen |
| Affected User | Who is impacted (all users / specific role / specific ID) |
| Frequency | Always / Intermittent / One-time |
| Attachments | Screenshot or log reference (optional) |

Display collected intake:

```
## Bug Report

**Summary:** [bug_summary]
**Environment:** [environment]
**Frequency:** [frequency]
**Affected:** [affected_user]

**Reproduction Steps:**

1. [step 1]
2. [step 2]
...

**Observed:** [observed]
**Expected:** [expected]

```

**Gate:** Confirm intake is complete and accurate before scoring.

---

## Phase 2 — Severity Scoring 🟡 REVIEW

Score bug severity using this matrix:

| Severity | Criteria | Response Time |
| --- | --- | --- |
| **P1 — Critical** | Data loss · security breach · system down · payment failure · all users blocked | Immediate |
| **P2 — Major** | Key feature broken · significant UX degradation · partial data issue · majority of users affected | Next sprint |
| **P3 — Minor** | Cosmetic · edge case · workaround exists · rare frequency | Backlog |

Display scoring decision:

```
## Severity Assessment

**Severity:** [P1/P2/P3] — [label]
**Rationale:** [why this severity was chosen]
**Response:** [response time expectation]

```

Present to user — auto-proceed unless user objects (🟡 REVIEW).

---

## Phase 3 — Duplicate Check 🟢 AUTO

Search for existing bugs before creating a new one.

1. Run `cache_search(query="[bug_summary]", limit=5)` for semantic matches
2. Run `jira_search(jql="project = BEP AND issuetype = Task AND text ~ '[keywords]' ORDER BY created DESC", fields="summary,status,assignee")` with extracted keywords

If duplicate found:

```
⚠️ Possible duplicate detected: [KEY] — [summary] ([status])
Link: https://{{JIRA_SITE}}/browse/[KEY]

Options:

  1. Link to existing issue (add comment with new repro steps)
  2. Create as separate issue (different root cause or environment)

```

If no duplicate found: auto-proceed silently.

---

## Phase 4 — Assign ⛔ GATE

Recommend assignee based on affected service tag and team skill matrix:

```
## Assignment Recommendation

**Affected Service:** [service tag: BE/FE-Admin/FE-Web/Video]
**Recommended Assignee:** [name] — [role] ([rationale])
**Fallback:** [alternative name]

```

Wait for user to confirm or override assignee. Record `assignee_email` from `team.members[]`.

---

## Phase 5 — Create Jira Task 🟢 AUTO

Generate ADF JSON for bug task, then create via acli.

**Summary format:** `[Bug][P1/P2/P3] [bug_summary]`

**ADF structure** (use `templates-task.md` bug template):

```
🐛 Bug Description (panel: error)
🔄 Reproduction Steps (numbered list)
📊 Expected vs Actual (table: 2 columns)
🌍 Environment (panel: note)
👥 Affected Users (inline)
📎 Attachments (if any)
✅ Fix Criteria (panel: success)

```

**Quality Gate:** T1–T5 technical checks + bug-specific checks:

| Check | Criterion |
| --- | --- |
| B1 | Summary includes severity label [P1/P2/P3] |
| B2 | Reproduction steps are numbered and specific |
| B3 | Expected vs Actual is explicit (not combined) |
| B4 | Environment field is filled |
| B5 | Fix criteria are testable and specific |

QG must be ≥ 90% before creation. HR1 enforced.

**Create:**

```bash
acli jira workitem create --from-json {{artifacts_dir}}/bep-xxx-bug.json
```

**After create:**

```bash
# HR3: assign via acli (MCP assignee silently fails)
acli jira workitem assign -k "[issue_key]" -a "[assignee_email]" -y
```

Add severity label:

```python
jira_update_issue(issue_key="[issue_key]", additional_fields={"labels": ["P1"] | ["P2"] | ["P3"]})
```

> **HR6:** `cache_invalidate(issue_key)` after each write.

---

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

---

## Common Scenarios

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.

---

## References

- [ADF Core Rules](../shared-references/templates-core.md)
- [Task Template](../shared-references/templates-task.md) — bug template section
- [Verification Checklist](../shared-references/verification-checklist.md)
- [Tools Reference](../shared-references/tools.md) — acli vs MCP decision
- [Scenarios](references/scenarios.md) - Command examples by scenario
- After: `/verify-issue [KEY]` to check quality
- After fix: `/create-testplan [KEY]` to create QA verification subtask
