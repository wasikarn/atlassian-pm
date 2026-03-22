---
name: bug-triage
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Structured bug triage workflow for QA: intake → severity scoring → duplicate check → assign → create Jira Task.
  Distinct from /create-task bug (which is just ticket creation). This skill is a full triage workflow.
  Triggers: "bug triage", "triage bug", "report bug", "new bug", "bug found", "จัดการ bug", "รายงาน bug"
  Use when: triaging an incoming bug report — severity scoring, dedup check, assignment, and Jira creation
  Do NOT use for: creating a simple task (use create-task); creating a story (use create-story)
argument-hint: "[description]"
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
2. Run `jira_search(jql="project = {{PROJECT_KEY}} AND issuetype = Task AND text ~ '[keywords]' ORDER BY created DESC", fields="summary,status,assignee")` with extracted keywords

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

## Examples

### ✅ Good

```text
/bug-triage                                                        # start interactive intake from scratch
/bug-triage "Upload fails silently after selecting a file > 10MB"  # pre-fills summary, agent collects remaining fields
/bug-triage "Payment confirmation email not sent in production"     # clear, actionable summary for P1 candidate
/bug-triage "Admin user list shows wrong pagination count"          # scoped description → fast severity scoring
```

### ❌ Bad

```text
/create-task bug "Upload broken"           # skips severity scoring, duplicate check, and assignee recommendation — use /bug-triage
/bug-triage "It's broken"                  # intake too vague; agent cannot score severity without repro steps and environment
/bug-triage "{{PROJECT_KEY}}-99"                       # passing an issue key makes no sense here — triage creates a new ticket
/bug-triage "CSS misaligned on mobile"     # cosmetic P3 does not need full triage workflow — /create-task bug is sufficient
```

**Common mistakes:**

- Using `/create-task bug` when the bug needs severity scoring (P1/P2/P3), duplicate check, and smart assignee recommendation — those phases only exist in `/bug-triage`
- Skipping Phase 1 confirmation before proceeding to scoring — all intake fields (repro steps, environment, frequency, affected users) must be complete; incomplete intake produces wrong severity
- Assigning a P1 Critical bug directly to a junior developer without flagging for senior review — Phase 4 recommendation logic accounts for skill level
- Not checking for duplicates (Phase 3 is mandatory before creation) — creating duplicate tickets wastes sprint capacity and splits the fix effort

## References

- [ADF Core Rules](../../../references/templates-core.md)
- [Task Template](../../../references/templates-task.md) — bug template section
- [Verification Checklist](../../../references/verification-checklist.md)
- [Tools Reference](../../../references/tools.md) — acli vs MCP decision
- [Scenarios](references/scenarios.md) - Command examples by scenario
- After: `/verify-issue [KEY]` to check quality
- After fix: `/create-testplan [KEY]` to create QA verification subtask

## 🎓 Domain Expert Notes

### Why This Approach

Bug triage separates _severity_ (technical impact on the system) from _priority_ (business decision on when to fix), preventing critical data-loss bugs from sitting in the backlog because a stakeholder did not flag them as urgent. The structured intake-before-scoring sequence ensures the severity decision is always evidence-based, not reactive.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| ITIL Incident Classification | Phase 2 severity matrix (P1/P2/P3) | Aligns bug severity to service-impact tiers used in enterprise incident management |
| ISO/IEC 25010 Quality Characteristics | Phase 2 criteria (security, reliability, usability) | Provides a principled vocabulary for "what makes a bug critical" beyond gut feel |
| DORA Change Failure Rate | Post-sprint defect tracking via P1/P2 labels | P1 bugs contribute to change failure rate; tracking them enables MTTR measurement |
| Defect Life Cycle (IEEE 1044) | Phases 1–5 workflow (intake → assign → create) | Standard defect workflow ensures full traceability from detection to resolution |

### Key Metrics

- **Defect Escape Rate:** % of bugs found in production vs. QA — target < 10%; high escape rate signals weak test coverage in `/create-testplan`
- **MTTR (Mean Time to Resolve):** Time from bug creation to Done status — P1 target < 24h, P2 < 1 sprint, P3 < 3 sprints
- **Duplicate Rate:** % of triage sessions that find a duplicate in Phase 3 — > 20% signals missing test coverage or poor story decomposition
- **Severity Distribution:** Healthy backlog = < 5% P1, < 30% P2, > 65% P3 — inversion signals systemic quality problems

### Expert Decision Criteria

**Severity vs Priority distinction (common confusion):**

- _Severity_ = technical damage (data loss, system down, security breach) — set by QA/engineer in Phase 2
- _Priority_ = business urgency (when to fix) — set by product owner, may override severity
- A P1 severity bug on a deprecated feature may have low business priority — document the divergence explicitly

**P1 escalation triggers (immediate action required):**

- Any bug involving PII exposure or auth bypass → Security incident, not just bug triage
- Payment or financial transaction failure → Escalate to Tech Lead within 15 minutes
- Database corruption or data loss → Freeze deployments, notify all stakeholders

**Assignee skill matching (Phase 4):**

- Backend-only bugs → assign to BE developer; avoid assigning to junior without senior pairing for P1
- Cross-service bugs → assign to Tech Lead for root cause analysis first, then delegate fix
- Intermittent bugs → always assign to senior developer; intermittent = complex race condition or infra issue

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| P1 bugs found only in production | QA test plan does not cover critical paths | After fix, use `/create-testplan` with explicit regression cases for the affected path |
| Duplicate bugs split the fix effort | Phase 3 skipped or keywords too narrow in JQL | Always search both semantic (`cache_search`) and keyword (`jira_search`) before creating |
| Severity scores keep getting changed post-triage | Incomplete intake in Phase 1 (frequency, affected users missing) | Gate Phase 1 strictly — all 8 intake fields required before proceeding to scoring |
| P1 bug assigned to junior developer | Phase 4 recommendation logic bypassed by user | Enforce: P1 assignee must have `backend: expert` or `frontend_admin: expert` in skill_profile |
| Bug backlog grows without resolution | No MTTR tracking; severity labels not reviewed in sprint planning | Add P1/P2/P3 label filters to sprint board; review aging P2s in every sprint planning session |

### Authoritative References

- **ITIL 4 (Axelos):** Incident severity levels — the P1/P2/P3 matrix directly maps to ITIL's Critical/High/Medium service impact tiers
- **ISO/IEC 25010:2011 (SQuaRE):** System quality model — security, reliability, and usability characteristics define what constitutes a "critical" bug
- **DORA (Accelerate, Forsgren et al.):** Change failure rate and MTTR are two of the four key DevOps metrics; bug severity labeling feeds these measurements directly
- **IEEE 1044-2009:** Standard classification of software anomalies — provides the formal basis for defect lifecycle phases used in this skill
