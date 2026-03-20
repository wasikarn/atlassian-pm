---
name: create-task
disable-model-invocation: true
x-compatibility: [jira-cache-server, mcp-atlassian, acli]
description: |
  Create a new Jira Task with a 5-phase workflow
  Supports 4 task types: tech-debt, bug, chore, spike

  Triggers: "create task", "new task"
argument-hint: "[type] [description]"
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

> **🟢 AUTO** — [QG Scoring Rules](../../shared-references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`
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

## References

- [ADF Core Rules](../../shared-references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Task Template](../../shared-references/templates-task.md) - Task ADF templates (tech-debt, bug, chore, spike)
- [Scenarios](references/scenarios.md) - Command examples and full example
- After: `/verify-issue ABC-XXX` to check quality
