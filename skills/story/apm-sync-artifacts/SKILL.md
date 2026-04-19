---
name: apm-sync-artifacts
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
allowed-tools: Read, Bash, Agent, Write, Edit, TodoWrite, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_search, mcp__mcp-atlassian__jira_update_issue, mcp__mcp-atlassian__confluence_get_page, mcp__mcp-atlassian__confluence_search, mcp__mcp-atlassian__confluence_update_page, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Bidirectional sync for Jira issues and Confluence pages that have drifted out of alignment. Syncs all related artifacts (Epic, Task, QA, Confluence) using an 8-phase workflow.

  Phases: Identify Origin → Build Graph → Detect Changes → Impact Analysis → Explore (if needed) → Generate Updates → Execute Sync → Verify & Report

  Triggers: "sync alignment", "sync all", "update related", "cascade all", "sync drift", "out of sync", "this task is outdated", "cascade changes", "sync with parent", "ซิงค์ artifacts", "อัปเดตทุกอย่าง"
  Use when: Jira issues and Confluence pages have drifted out of alignment
  Do NOT use for: initial issue creation (use create-task) or individual field updates (use update-task)
argument-hint: "[issue-key-or-page-id] [changes]"
effort: high
---

# /atlassian-pm:apm-sync-artifacts

**Role:** PO + TA + Tech Lead Combined
**Output:** Updated Jira issues + Confluence pages (all related artifacts)

## Context Object (accumulated across phases)

| Phase | Adds to Context |
| ----- | --------------- |
| 1. Origin | `origin_key`, `origin_type`, `change_description` |
| 2. Graph | `artifact_graph[]`, `sync_scope` |
| 3. Changes | `change_type`, `impact_level`, `classified_changes[]` |
| 4. Impact | `impact_map[]`, `sync_plan` |
| 5. Explore | `file_paths[]`, `patterns[]` (conditional) |
| 6. Generate | `jira_updates[]`, `confluence_updates[]` |
| 7. Execute | `applied_keys[]`, `execution_log` |
| 8. Verify | `verification_report` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

## Artifact Graph

```text
Epic (Jira)
├── Epic Doc (Confluence parent page) — task list, status summary
├── Task 1 (Jira) — ACs, scope, implementation hints
│   └── Tech Note (Confluence child page) — technical details, API, DB
├── Task 2 (Jira)
│   └── Tech Note (Confluence)
└── ...
```

## Phases

### 1. Identify Origin

- Receive input: `{{PROJECT_KEY}}-XXX` (Jira key) or Confluence page ID
- `jira_get_issue(issue_key, fields="summary,status,issuetype,parent")`
- Determine artifact type: Epic / Task
- If Confluence page ID → `confluence_get_page(page_id)` → extract {{PROJECT_KEY}} keys → pivot to Jira
- **⛔ GATE** — Requires user confirmation of starting artifact + description of what changed before proceeding.

### 2. Build Artifact Graph

Discovery algorithm:

```text
1. jira_get_issue(origin, fields="summary,status,issuetype,parent")
2. Walk UP:
   - if Task → parent_epic = issue.parent
3. Walk DOWN:
   - jira_search("parent = EPIC_KEY AND issuetype = Task", fields="summary,status,issuetype,parent") → tasks
   ⚠️ Do not add ORDER BY to parent queries — causes JQL parse error (HR2)
4. Walk SIDEWAYS (Jira → Confluence):
   - per task: confluence_search("{{PROJECT_KEY}}-XXX") → Tech Note
   - epic: confluence_search(epic_title) → Epic Doc
```

Fetch only `fields="summary,status,issuetype,parent"` (no description). Output: inventory table (Type, Key/ID, Title, Status).

**🟡 REVIEW** — Present artifact graph + scope options. User selects: Full / Jira-only / Confluence-only / Selective.

### 3. Detect Changes

User describes changes, then classify:

| Change Type | Impact Level |
| --- | --- |
| Format only / Clarify wording | LOW |
| Add AC / Modify AC / Technical detail | MEDIUM |
| Remove AC / Change scope / Business value | HIGH |

**⛔ GATE** — Requires user confirmation of change classification before proceeding.

### 4. Impact Analysis

Map changes → affected artifacts table (Artifact, Impact, Reason).

Impact types: `ORIGIN` / `UPDATE` / `FLAG` / `NO CHANGE`
Directions: DOWN (parent→child) / UP (child→parent) / SIDEWAYS (Jira↔Confluence)

**🟡 REVIEW** — Present impact table + sync plan. Proceed unless user objects.

### 5. Codebase Exploration (conditional)

> **🟢 AUTO** — Run only if scope changed or new file paths needed. Skip if format-only. Validate paths with Glob.

[Parallel Explore](../../../references/workflow-patterns.md#parallel-explore): Launch 2-3 agents (Backend/Frontend/Shared) IN PARALLEL. Generic paths REJECTED.

### 6. Generate Sync Updates

Fetch full description only for artifacts with impact = UPDATE:

**Per Jira issue:** `jira_get_issue(issue_key, fields="summary,description")` → generate ADF JSON → `{{artifacts_dir}}/sync-tp-xxx.json` → show before/after.

**Per Confluence page:** `confluence_get_page(page_id)` → surgical find/replace pairs, section update, or full rewrite → `{{artifacts_dir}}/sync-page-xxx.md`

**⛔ GATE** — Requires user approval of ALL generated updates before executing any sync.

### 7. Execute Sync

> **🟢 AUTO** — QG check → execute in order → cache invalidate. Escalate only on failure.
> HR1: Score all Jira ADF updates before execution. QG ≥ 90% required.

```bash
uv run scripts/api/validate_adf.py {{artifacts_dir}}/sync-tp-*.json --type [auto-detect] --json
# Score ≥ 90 = PASS. If FAIL → check issues[].fix_hint → --fix → re-score. Max 1 fix cycle.
```

Order: Parents first → Children → Confluence

| Change Type | Jira Tool | Confluence Tool |
| --- | --- | --- |
| Rewrite description | `acli --from-json` (ADF) | `create_confluence_page.py --page-id` |
| Text replacement | `update_jira_description.py` | `update_confluence_page.py --find --replace` |
| Fields only | MCP `jira_update_issue` | — |
| Code blocks/macros | — | `update_page_storage.py` |

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after EVERY write · HR3: assignee via `acli jira workitem assign` · HR4: Confluence macros → `update_page_storage.py` · HR5: New tasks → Two-Step + Verify Parent.

### 8. Verify & Report

> **🟢 AUTO** — Verify all artifacts automatically. Report results.

`audit_confluence_pages.py --config {{artifacts_dir}}/sync-audit.json`

Output: Summary table (Artifact, Action, Status) + flagged items.

Post-sync: `rm {{artifacts_dir}}/sync-*.json {{artifacts_dir}}/sync-*.md` → `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks`

## Examples

### ✅ Good

```text
/sync-artifacts {{PROJECT_KEY}}-42 "added new AC for error handling"    # sync from Jira task to all related
/sync-artifacts {{PROJECT_KEY}}-100 "scope reduced, remove v2 features" # sync epic + all children + docs
/sync-artifacts 123456 "Confluence page outdated"          # sync from Confluence page ID
```

### ❌ Bad

```text
/sync-artifacts                          # no issue key or page ID — cannot identify origin
/sync-artifacts {{PROJECT_KEY}}-42                    # no change description — Phase 3 gate will ask
/sync-artifacts {{PROJECT_KEY}}-42 "fix typo"         # format-only change — use /update-task for simple edits
```

**Common mistakes:**

- Syncing without describing changes — impact analysis needs to know what changed
- Using sync-artifacts for single-field updates — use `/update-task` or `/update-epic` for simple changes
- Skipping the QG check — HR1 requires QG ≥ 90% before any Jira write

## References

[ADF Core Rules](../../../references/templates-core.md) · [Templates Index](../../../references/templates.md) · [Tool Selection](../../../references/tools.md) · [Verification Checklist](../../../references/verification-checklist.md) · [Atlassian Scripts](../../../skills/utilities/atlassian-scripts/SKILL.md) · [Edge Cases](references/edge-cases.md) · [Decision Guide](references/decision-guide.md)
