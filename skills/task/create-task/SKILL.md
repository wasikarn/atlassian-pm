---
name: create-task
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Create a new Jira Task — vibe mode by default (fast, auto-detect type)
  Supports 4 task types: tech-debt, bug, chore, spike
  Use --thorough for full interview + review gates

  Triggers: "create task", "new task", "สร้าง task", "tech debt task", "add chore", "new spike"
  Use when: creating a standalone task — tech-debt, bug, chore, or spike — that is not a User Story
  Do NOT use for: User Stories (use create-story); epics (use create-epic); full bug triage with severity/dedup/assign (use bug-triage)
argument-hint: "[--thorough] [type] [description]"
effort: medium
---

# /create-task

**Role:** Developer / Tech Lead
**Output:** Jira Task with ADF format

## Mode Selection

| Flag | Behavior | User interactions |
| --- | --- | --- |
| *(none)* | **Vibe mode (default)** — auto-detect type from description, single-pass generation, no review gate | 0–1 (only if type is ambiguous) |
| `--thorough` | **Thorough mode** — full interview, explicit type selection, review gate before creation | Multiple checkpoints |

> If the argument contains `--thorough`, strip the flag and treat the remaining text as `[type] [description]`. Proceed with thorough mode for all phases.

## Task Types

| Type | Use Case | Example |
| --- | --- | --- |
| `tech-debt` | PR review issues, code improvements, refactoring | Fix issues from code review |
| `bug` | Bug fixes from QA or production | Fix bug reported by QA |
| `chore` | Maintenance, dependency updates, configs | Update dependencies |
| `spike` | Research, investigation, POC | Evaluate a new library |


## Phases

### 1. Discovery

#### Vibe Mode (Default)

Auto-detect task type from description keywords:
- "fix", "bug", "broken", "error" → `bug`
- "debt", "refactor", "cleanup", "improve" → `tech-debt`
- "update", "maintain", "config", "dependency" → `chore`
- "research", "investigate", "evaluate", "POC" → `spike`

If type cannot be inferred → ask ONE question: "What type? (tech-debt/bug/chore/spike)"

Auto-extract required details from the description argument. Proceed to Phase 2 immediately.

#### --thorough Mode

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

**⛔ GATE:** User provides required info


### 2. Generate Template

> **⚠️ MANDATORY:** Read `references/templates-task.md` before generating any ADF. All sections use `panel` ADF nodes — NEVER use `heading` nodes in task descriptions.

Generate ADF JSON based on task type → `{{artifacts_dir}}/tp-xxx-task.json`

**tech-debt Template:**

```json
{
  "projectKey": "<project_key>",
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
  "projectKey": "<project_key>",
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
  "projectKey": "<project_key>",
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
  "projectKey": "<project_key>",
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


### 3. Review

#### Vibe Mode (Default)

- **No review gate** — proceed directly to Quality Gate after generation.

#### --thorough Mode

Show preview for user to review:

```text
## Task Preview

**Type:** [tech-debt/bug/chore/spike]
**Summary:** [summary]

**Sections:**
- [list of sections with emoji]

**Files:** {{artifacts_dir}}/tp-xxx-task.json

Any changes needed before creating?
```

**Gate:** User approves content


### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — [QG Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`
> HR1: DO NOT send Task to Atlassian without QG ≥ 90%.
>
> **🟢 AUTO (validate_adf.py):**
>
> ```bash
> uv run scripts/api/validate_adf.py {{artifacts_dir}}/tp-xxx-task.json --type task --json
> ```
>
> Score ≥ 90 = PASS. If FAIL → check `issues[].fix_hint` → run `--fix` → re-score. Max 1 fix cycle.

### 5. Create

```bash
acli jira workitem create --from-json {{artifacts_dir}}/tp-xxx-task.json
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


### 6. Summary

```text
## ✅ Task Created: [Title] (ABC-XXX)

**Type:** [type]
**Priority:** [High/Medium/Low]

🔗 [View in Jira](https://{{JIRA_SITE}}/browse/ABC-XXX)

→ Use /verify-issue ABC-XXX to check quality
→ Use /update-task ABC-XXX to add details later
```


## Common Scenarios

> See [references/scenarios.md](references/scenarios.md) for command examples by scenario.


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

[ADF Core Rules](../../../references/templates-core.md) · [Task Template](../../../references/templates-task.md) · [Scenarios](references/scenarios.md)

After: `/verify-issue ABC-XXX` to check quality

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)