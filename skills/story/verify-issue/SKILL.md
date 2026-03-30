---
name: verify-issue
context: fork
agent: general-purpose
model: sonnet
x-compatibility: [atlassian-cache, mcp-atlassian, acli]
allowed-tools: Read, Glob, Grep, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__mcp-atlassian__confluence_search, mcp__mcp-atlassian__confluence_get_page
description: |
  Verify and improve issue quality (ADF format, INVEST, language, hierarchy alignment) with a 6-phase workflow

  Checks: ADF render, panel structure, links, inline code, INVEST criteria, Given/When/Then, file paths, language consistency, hierarchy alignment (Epic↔Story↔Subtasks↔Docs)

  Supports: --with-subtasks (batch + alignment check), --fix (auto-fix + format migration)

  Triggers: "verify", "validate", "check quality", "improve", "migrate format", "QG score", "quality gate", "ตรวจสอบ issue"
  Use when: quality-checking ADF format, INVEST criteria, or hierarchy alignment of any issue before or after creation
  Do NOT use for: creating issues (use create-story/create-epic/create-task); deliberate scope or AC rewrites (use update-story/update-epic)
argument-hint: "[issue-key] [--with-subtasks] [--fix] [--dry-run]"
effort: medium
---

# /verify-issue

**Role:** Any | **Output:** Verification report (default) or Improved issues (`--fix`)

## Phases

### 1. Fetch & Identify

- `jira_get_issue(issue_key)` — fetch issue
- If `--with-subtasks` → `jira_search(jql: "parent = ABC-XXX", fields: "summary,status,assignee,issuetype")` (**⚠️ HR2: NEVER add ORDER BY**)
- Identify type → select checklist; build inventory: Key, Type, Current Format
- **Gate (--fix only):** User confirms scope

### 2. Technical Verification

ADF `type:"doc"` · correct `panelType` · technical terms inline-coded · parent/child links exist · required fields filled.

### 3. Quality Verification

Score ⭐–⭐⭐⭐⭐⭐ per dimension: Format (ADF+panels+inline code) · Language (Thai+loanwords) · Structure (follows template) · Completeness (all sections) · Clarity (ACs testable, Given/When/Then).

> **🟢 AUTO (validate_adf.py):**
> `uv run scripts/api/validate_adf.py {{artifacts_dir}}/[issue_key].json --type [epic|story|subtask|task] --json`
> Score ≥ 90 = PASS. If FAIL → check `issues[].fix_hint` → run `--fix` → re-score. Max 1 fix cycle.

**Type-specific checks:**

- **Story:** INVEST criteria (6 points), Narrative format, AC Given/When/Then
- **Sub-task:** Objective clear, File paths real (not generic), AC format correct
- **QA:** All Story ACs covered, Test scenarios clear, Priority assigned

### 4. Hierarchy Alignment (`--with-subtasks` only)

> Use only real data from Jira/Confluence — never guess. Unclear AC→subtask mapping → flag "unclear mapping".

**Data fetching:**

1. `jira_get_issue(story_key)` — ACs, scope, services (must come first for story.parent key)
2. Then in parallel: `jira_get_issue(story.parent)` (Epic scope) + `confluence_search("ABC-XXX")` (Tech Note) — skip if none

(Subtasks already in memory from Phase 1)

**Alignment checks:** A1 AC↔Subtask (every AC ≥1 subtask) · A2 Service tag match · A3 Scope consistency · A4 Epic↔Story fit (skip if no Epic) · A5 Parent-child links correct · A6 Confluence↔ACs aligned (skip if no page, flag as info).

> **Agent invocation:** `Agent(name: "alignment-checker", story_key: "[STORY-KEY]", mode: "--fix" | "read-only")`

### 5. Report

Output table: Category (Technical/Quality/Alignment) × Score × Status (✅/⚠️/❌); numbered issue list; suggest `--fix` if any failures. Alignment column shown only when `--with-subtasks`.

### 6. Fix (`--fix` only)

1. **Load Templates** — fetch template from `shared-references/`
2. **Generate** — preserve intent, apply template + ADF + Thai + inline code → `{{artifacts_dir}}/tp-xxx-fixed.json`
3. **Gate:** User approves. If auto-fixable ADF issues found: `Agent(name: "adf-surgeon", file_path: {{artifacts_dir}}/[issue_key].json, issues: [list])` — structural fixes only; verify changelog.
4. **Apply** — `acli jira workitem edit --from-json {{artifacts_dir}}/tp-xxx-fixed.json --yes`
5. **Cleanup** — `rm {{artifacts_dir}}/tp-*-fixed.json`; HR6: `cache_invalidate(issue_key)`

## Batch Mode (`--with-subtasks`)

Runs all 6 phases for story + each subtask. Output table: Key × Technical × Quality × Alignment × Overall.

## Common Scenarios

> See [references/scenarios.md](references/scenarios.md) for command examples, integration workflows, and a full example run.

## 🎓 Domain Expert Notes

See [references/domain-expert.md](references/domain-expert.md)

## References

[Verification Checklist](../../../references/verification-checklist.md) · [ADF Core Rules](../../../references/templates-core.md) · [Templates Index](../../../references/templates.md) · [Writing Style](../../../references/writing-style.md) · [Scenarios](references/scenarios.md)
