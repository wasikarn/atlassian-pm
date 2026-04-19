---
name: apm-create-task
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Creates a new Jira Task in vibe mode (fast, auto-detect type) by default. Use --thorough flag for full interview workflow.

  Supports 4 task types: tech-debt, bug, chore, spike
  Supports modes: feature (default), qa, bug, spike, chore

  Triggers: "create task", "new task", "add task", "create a task", "สร้าง task", "tech debt task", "tech-debt task", "create tech debt", "add tech debt", "add chore", "new spike", "create spike", "create bug task"
  Use when: creating a standalone task — feature, tech-debt, bug, chore, or spike — under an Epic
  Do NOT use for: epics (use create-epic); full bug triage with severity/dedup/assign (use bug-triage)
argument-hint: "[--qa|--bug|--spike|--chore] [description or issue-key]"
effort: medium
---

# /atlassian-pm:apm-create-task

**Role:** Developer / Tech Lead · **Output:** Jira Task (ADF)

**Modes:** *(none)* = vibe (auto-detect, no review gate, 0–1 interactions) · `--thorough` = full interview + review gate. Strip `--thorough` flag before processing remaining args.

**Types:** `tech-debt` (PR issues, refactor) · `bug` (QA/prod fixes) · `chore` (maintenance, deps) · `spike` (research, POC)

> **See [Scenarios](references/scenarios.md) for common usage patterns.**

## Mode Selection

| Flag | Mode | Template |
| --- | --- | --- |
| *(none)* | feature (default) | สิ่งที่ผู้ใช้ต้องการ + เงื่อนไขที่ต้องผ่าน + ขอบเขตไฟล์ + คำแนะนำการพัฒนา |
| `--qa` | QA test plan | วัตถุประสงค์ทดสอบ + ชุดทดสอบ |
| `--bug` | Bug report | รายละเอียดปัญหา + ขั้นตอนทำซ้ำ + คาดหวัง vs เกิดจริง + เงื่อนไขที่ต้องผ่าน |
| `--spike` | Research spike | คำถามวิจัย + บริบท + พื้นที่สำรวจ |
| `--chore` | Maintenance | วัตถุประสงค์ + รายการงาน + เงื่อนไขที่ต้องผ่าน |

> **Auto-detect:** If no flag, infer mode from content: "test"/"QA"/"ทดสอบ" → qa, "bug"/"error"/"พัง" → bug, "research"/"วิจัย"/"spike" → spike, "chore"/"upgrade"/"config" → chore

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
> `{{artifacts_dir}}` is the session artifact directory (default: `~/.claude/artifacts/`).
>
> PASS ≥ 90. FAIL → check `issues[].fix_hint` → `--fix` → re-score. Max 1 fix cycle.

### 5. Create

`acli jira workitem create --from-json {{artifacts_dir}}/tp-xxx-task.json` — capture issue key.

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after create.

`jira_update_issue(issue_key, additional_fields={"customfield_10016": <SP>, "customfield_10107": {"value": "<SIZE>"}, "timetracking": {"originalEstimate": "<N>h"}})`

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after update.

### 6. Summary

Output: `✅ Task Created: [Title] (ABC-XXX) · Type: [type] · Priority: [H/M/L] · 🔗 https://{{JIRA_SITE}}/browse/ABC-XXX · → /verify-issue ABC-XXX`

## Examples

### ✅ Good

```text
/create-task "Add password reset feature"                    # vibe mode (auto-detect type)
/create-task --bug "Login fails with special characters"    # bug mode with description
/create-task --spike "Research GraphQL migration path"       # spike mode
/create-task --chore "Upgrade Node.js to v24"                # chore mode
/create-task --thorough "Refactor auth module"               # full interview workflow
/create-task {{PROJECT_KEY}}-50 "Implement video upload API" --thorough  # with parent epic specified
```

### ❌ Bad

```text
/create-task                                                # no description — stalls at discovery
/create-task --bug                                          # bug mode without description — stalls
/create-task "Fix the bug"                                  # too vague — needs specific description
/create-task --feature "Add feature"                        # --feature is not a valid mode
/create-task {{PROJECT_KEY}}-50                                          # parent key alone without description
```

**Common mistakes:**

- Omitting description entirely — vibe mode still needs a description to infer type
- Using `--feature` flag — feature is the default, just omit the flag
- Providing only parent epic without task description — both are needed
- Skipping QG check for "simple" tasks — HR1 requires QG ≥ 90% for all ADF

## References

[ADF Core Rules](../../../references/templates-core.md) · [Task Template](../../../references/templates-task.md) · [Scenarios](references/scenarios.md)

## 🎓 Domain Expert Notes

See [references/expert-notes.md](references/expert-notes.md)
