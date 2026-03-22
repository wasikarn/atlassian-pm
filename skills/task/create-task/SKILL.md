---
name: create-task
disable-model-invocation: true
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Create a new Jira Task with a 6-phase workflow
  Supports 4 task types: tech-debt, bug, chore, spike

  Triggers: "create task", "new task", "สร้าง task", "tech debt task", "add chore", "new spike"
  Use when: creating a standalone task — tech-debt, bug, chore, or spike — that is not a User Story
  Do NOT use for: User Stories (use create-story); epics (use create-epic); full bug triage with severity/dedup/assign (use bug-triage)
argument-hint: "[type] [description]"
effort: medium
---

# /create-task

**Role:** Developer / Tech Lead
**Output:** Jira Task with ADF format

## Task Types

| Type | Use Case | Example |
| --- | --- | --- |
| `tech-debt` | PR review issues, code improvements, refactoring | Fix issues from code review |
| `bug` | Bug fixes from QA or production | Fix bug reported by QA |
| `chore` | Maintenance, dependency updates, configs | Update dependencies |
| `spike` | Research, investigation, POC | Evaluate a new library |

---

## Phases

### 1. Discovery

Ask user to gather information:

**If type not specified:**

```text
What type of Task do you want to create?
1. tech-debt - Code improvements, PR review issues
2. bug - Bug fixes
3. chore - Maintenance tasks
4. spike - Research/Investigation
```

**Gather details by type:**

| Type | Required Info |
| --- | --- |
| `tech-debt` | Context, Issues (priority), ACs |
| `bug` | Description, Repro steps, Expected/Actual |
| `chore` | Objective, Task list |
| `spike` | Research question, Investigation areas |

**Gate:** User provides required info

---

### 2. Generate Template

Generate ADF JSON based on task type → `{{artifacts_dir}}/bep-xxx-task.json`

**tech-debt Template:**

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Task",
  "summary": "[BE/FE] [Title]",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      // 📋 Context (panel: info)
      // 🔴 HIGH Priority (panel: error) - if any
      // 🟡 MEDIUM Priority (panel: warning) - if any
      // 🟣 LOW Priority (panel: note) - if any
      // ✅ Acceptance Criteria (table)
      // 🔗 Reference (table)
    ]
  }
}
```

**bug Template:**

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Task",
  "summary": "[Bug] [Title]",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      // 🐛 Bug Description (panel: error)
      // 🔄 Reproduction Steps (numbered list)
      // 📊 Expected vs Actual (table)
      // 🔍 Root Cause (panel: note) - optional
      // ✅ Fix Criteria (panel: success)
      // 🔗 Reference (table)
    ]
  }
}
```

**chore Template:**

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Task",
  "summary": "[Chore] [Title]",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      // 🎯 Objective (panel: info)
      // 📋 Tasks (checklist in panel)
      // 🔗 Reference (table)
    ]
  }
}
```

**spike Template:**

```json
{
  "projectKey": "{{PROJECT_KEY}}",
  "type": "Task",
  "summary": "[Spike] [Title]",
  "description": {
    "type": "doc",
    "version": 1,
    "content": [
      // ❓ Research Question (panel: info)
      // 📋 Context (paragraph)
      // 🔍 Investigation Areas (bullet list)
      // 📝 Findings (panel: note) - placeholder
      // 💡 Recommendations (panel: success) - placeholder
      // 🔗 Reference (table)
    ]
  }
}
```

**Gate:** JSON file created

---

### 3. Review

Show preview for user to review:

```text
## Task Preview

**Type:** [tech-debt/bug/chore/spike]
**Summary:** [summary]

**Sections:**
- [list of sections with emoji]

**Files:** {{artifacts_dir}}/bep-xxx-task.json

Any changes needed before creating?
```

**Gate:** User approves content

---

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`
> HR1: DO NOT send Task to Atlassian without QG ≥ 90%.

### 5. Create

```bash
acli jira workitem create --from-json {{artifacts_dir}}/bep-xxx-task.json
```

**Capture issue key from output** for use in summary

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after create.

**Set estimation fields (after create):**

```text
MCP: jira_update_issue(issue_key="ABC-XXX", additional_fields={
  "customfield_10016": <SP>,                  # Story Points (XS=1,S=2,M=3,L=5,XL=8)
  "customfield_10107": {"value": "<SIZE>"},   # Size
  "timetracking": {"originalEstimate": "<N>h"} # Original Estimate
})
```

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after field update.

---

### 6. Summary

```text
## ✅ Task Created: [Title] (ABC-XXX)

**Type:** [type]
**Priority:** [High/Medium/Low]

🔗 [View in Jira](https://{{JIRA_SITE}}/browse/ABC-XXX)

→ Use /verify-issue ABC-XXX to check quality
→ Use /update-task ABC-XXX to add details later
```

---

## Common Scenarios

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.

---

## Examples

### ✅ Good

```text
/create-task tech-debt "Fix N+1 query in video list endpoint — flagged in PR #214"
/create-task bug "Upload button unresponsive after file validation error"
/create-task chore "Upgrade Node 20 → 24 across all services"
/create-task spike "Evaluate tRPC vs REST for admin API layer — output: ADR doc"
```

### ❌ Bad

```text
/create-task                              # missing type and description — agent must ask twice
/create-task bug "Login broken"           # full triage with severity scoring needed — use /bug-triage instead
/create-task spike "Investigate caching"  # no research question defined; spike requires clear investigation areas
/create-task "Refactor auth module"       # missing type — ambiguous between tech-debt and chore
```

**Common mistakes:**

- Using `bug` type when the bug needs P1/P2/P3 severity scoring, duplicate check, and assignee recommendation — use `/bug-triage` for that
- Creating a `tech-debt` task without referencing the PR number or commit that surfaced the issue (breaks traceability)
- Using `/create-task` for a User Story (feature with AC) — use `/create-story` instead
- Defining a `spike` without stating the research question and what deliverable (ADR, POC, benchmark) is expected at the end

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Task Template](../../../references/templates-task.md) - Task ADF templates (tech-debt, bug, chore, spike)
- [Scenarios](references/scenarios.md) - Command examples and full example
- After: `/verify-issue ABC-XXX` to check quality

## 🎓 Domain Expert Notes

### Why This Approach

Task decomposition quality directly determines sprint predictability: tasks with vague scope or missing acceptance criteria are the #1 cause of sprint carry-over. The four task types (tech-debt, bug, chore, spike) enforce distinct templates because each has fundamentally different done criteria — a spike is done when a decision is made, a chore when a checklist is complete, and tech-debt when the codebase metric improves.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SMART Criteria (Doran, 1981) | Phase 1 required info per type | Ensures tasks are Specific, Measurable, Achievable, Relevant, Time-bound before creation |
| Technical Debt Quadrant (Fowler) | `tech-debt` type classification | Distinguishes reckless/prudent debt — only prudent-deliberate debt belongs in a task |
| Spike Concept (XP/Scrum) | `spike` type template | Spikes have a fixed timebox and a concrete deliverable (ADR, POC, benchmark) — not open-ended research |
| Definition of Done (Scrum Guide) | Quality Gate checks T1–T5 | Each task type has type-specific done criteria baked into the QG checks |

### Key Metrics

- **Task Cycle Time:** Time from "In Progress" to "Done" — target 1–3 days per task; > 5 days signals task is too large (should be split)
- **Carry-over Rate:** % of tasks not completed within the sprint they were planned — target < 15%; high carry-over = poor estimation or scope creep
- **Spike Time-box Compliance:** Spikes should never exceed their stated timebox — a spike that expands is a poorly-scoped spike
- **Tech-debt Ratio:** SP allocated to tech-debt vs. features per sprint — healthy ratio is 15–20% tech-debt to prevent accumulation

### Expert Decision Criteria

**Task sizing thresholds (2-8 hour rule):**

- A task that takes < 2 hours of focused work should be a sub-task, not a standalone Task
- A task estimated > 8 hours should be split into multiple tasks or elevated to a Story with sub-tasks
- Spikes are always timeboxed: state the timebox explicitly in the summary (`[Spike][2d] Evaluate tRPC`)

**Type selection heuristics:**

- Has a PR review comment or linter violation as the origin → `tech-debt`
- Has a clear checklist of mechanical steps with no design decision → `chore`
- Has an unknown outcome and requires investigation before implementation can start → `spike`
- Has observable wrong behavior with repro steps but no severity scoring needed → `bug` (for full triage → `/bug-triage`)

**Traceability requirements:**

- `tech-debt`: must reference the PR number, commit SHA, or review comment that surfaced it
- `spike`: must state the research question AND the expected deliverable (ADR, benchmark, POC) in the summary
- `bug`: must state environment (staging/production) and affected user scope

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Tasks carry over every sprint | Tasks scoped too large (> 8h) or missing ACs | Apply 2-8h rule; ensure every task has testable acceptance criteria before sprint commit |
| Spike never produces a decision | No deliverable defined; open-ended research | Rewrite spike with explicit research question + deliverable type (ADR/POC/benchmark) + timebox |
| Tech-debt backlog grows silently | No PR-to-task traceability; debt recorded informally | Every PR review comment flagged as debt must link to a tech-debt Task within the same sprint |
| Chore tasks re-opened after "Done" | Checklist items were vague or incomplete | Use numbered task list in ADF; each item must be independently verifiable |
| Bug task lacks repro steps | Using `/create-task bug` for complex bugs needing triage | Route to `/bug-triage` for severity scoring, duplicate check, and assignee recommendation |

### Authoritative References

- **Martin Fowler (refactoring.com):** Technical Debt Quadrant — the definitive model for categorizing debt; only "prudent-deliberate" debt should become a planned task
- **Extreme Programming (Beck):** Spike concept — spikes are time-boxed experiments to reduce uncertainty; they always produce a concrete artifact
- **Scrum Guide (Schwaber & Sutherland):** Definition of Done — team-level agreement on what "complete" means; each task type in this skill encodes a type-specific DoD
- **Doran (1981) — Management Review:** SMART objectives — the framework behind the required-info per task type ensures every task is actionable from creation
