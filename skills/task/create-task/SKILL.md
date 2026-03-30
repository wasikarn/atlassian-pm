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

**Role:** Developer / Tech Lead · **Output:** Jira Task (ADF)

**Modes:** *(none)* = vibe (auto-detect, no review gate, 0–1 interactions) · `--thorough` = full interview + review gate. Strip `--thorough` flag before processing remaining args.

**Types:** `tech-debt` (PR issues, refactor) · `bug` (QA/prod fixes) · `chore` (maintenance, deps) · `spike` (research, POC)

## Phases

### 1. Discovery

**Vibe:** Infer type from keywords (fix/bug/broken→`bug` · debt/refactor/cleanup→`tech-debt` · update/maintain/config→`chore` · research/investigate/POC→`spike`). If ambiguous → ask ONE: "What type? (tech-debt/bug/chore/spike)". Proceed immediately.

**--thorough:** Ask type (1–4 menu). Collect: tech-debt→Context+Issues+ACs · bug→Description+Repro+Expected/Actual · chore→Objective+Task list · spike→Research question+Investigation areas.

**⛔ GATE:** User provides required info

### 2. Generate Template

> **⚠️ MANDATORY:** Read `references/templates-task.md` before generating any ADF. All sections use `panel` ADF nodes — NEVER use `heading` nodes.

Generate ADF JSON → `{{artifacts_dir}}/tp-xxx-task.json`

| Type | Summary prefix | Sections |
| --- | --- | --- |
| `tech-debt` | `[BE/FE] [Title]` | 📋 Context (info) · 🔴 HIGH / 🟡 MEDIUM / 🟣 LOW Priority panels · ✅ AC (table) · 🔗 Reference (table) |
| `bug` | `[Bug] [Title]` | 🐛 Bug Description (error) · 🔄 Repro Steps (numbered) · 📊 Expected vs Actual (table) · 🔍 Root Cause (note, optional) · ✅ Fix Criteria (success) · 🔗 Reference (table) |
| `chore` | `[Chore] [Title]` | 🎯 Objective (info) · 📋 Tasks (checklist) · 🔗 Reference (table) |
| `spike` | `[Spike] [Title]` | ❓ Research Question (info) · 📋 Context · 🔍 Investigation Areas · 📝 Findings (note, placeholder) · 💡 Recommendations (success, placeholder) · 🔗 Reference (table) |

All use `projectKey: "<project_key>", type: "Task"`.

**Gate:** JSON file created

### 3. Review

**Vibe Mode:** No review gate — proceed directly to Quality Gate.

**--thorough Mode:** Show preview (type, summary, sections list, file path). Ask for changes.

**⛔ GATE:** User approves content

### 4. Quality Gate (MANDATORY)

> **🟢 AUTO** — HR1: QG ≥ 90% required. [Scoring Rules](../../../references/workflow-patterns.md#quality-gate-scoring). Report: `Technical X/5 | Quality X/6 | Overall X%`
>
> ```bash
> uv run scripts/api/validate_adf.py {{artifacts_dir}}/tp-xxx-task.json --type task --json
> ```
>
> PASS ≥ 90. FAIL → check `issues[].fix_hint` → `--fix` → re-score. Max 1 fix cycle.

### 5. Create

`acli jira workitem create --from-json {{artifacts_dir}}/tp-xxx-task.json` — capture issue key.

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after create.

`jira_update_issue(issue_key, additional_fields={"customfield_10016": <SP>, "customfield_10107": {"value": "<SIZE>"}, "timetracking": {"originalEstimate": "<N>h"}})`

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after update.

### 6. Summary

Output: `✅ Task Created: [Title] (ABC-XXX) · Type: [type] · Priority: [H/M/L] · 🔗 https://{{JIRA_SITE}}/browse/ABC-XXX · → /verify-issue ABC-XXX`

## References

[ADF Core Rules](../../../references/templates-core.md) · [Task Template](../../../references/templates-task.md) · [Scenarios](references/scenarios.md)

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
