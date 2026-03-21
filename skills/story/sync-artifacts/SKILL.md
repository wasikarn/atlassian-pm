---
name: sync-artifacts
disable-model-invocation: true
context: fork
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Sync all related artifacts (Epic, Story, Sub-tasks, QA, Confluence) using an 8-phase workflow

  Phases: Identify Origin → Build Graph → Detect Changes → Impact Analysis → Explore (if needed) → Generate Updates → Execute Sync → Verify & Report

  ⭐ Composite: bidirectional sync from any artifact, covering both Jira + Confluence

  Triggers: "sync alignment", "sync all", "update related", "cascade all", "align artifacts"
argument-hint: "[issue-key-or-page-id] [changes]"
---

# /sync-artifacts

**Role:** PO + TA + Tech Lead Combined
**Output:** Updated Jira issues + Confluence pages (all related artifacts)

## Context Object (accumulated across phases)

| Phase | Adds to Context |
|-------|----------------|
| 1. Origin | `origin_key`, `origin_type`, `change_description` |
| 2. Graph | `artifact_graph[]`, `sync_scope` |
| 3. Changes | `change_type`, `impact_level`, `classified_changes[]` |
| 4. Impact | `impact_map[]`, `sync_plan` |
| 5. Explore | `file_paths[]`, `patterns[]` (conditional) |
| 6. Generate | `jira_updates[]`, `confluence_updates[]` |
| 7. Execute | `applied_keys[]`, `execution_log` |
| 8. Verify | `verification_report` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md) for Gate Levels (AUTO/REVIEW/APPROVAL), QG Scoring, Two-Step, and Explore patterns.

---

## Artifact Graph

```text
Epic (Jira)
├── Epic Doc (Confluence parent page) — story list, status summary
├── Story 1 (Jira) — ACs, scope
│   ├── Tech Note (Confluence child page) — technical details, API, DB
│   ├── Sub-task [BE] (Jira)
│   ├── Sub-task [FE-Admin] (Jira)
│   └── Sub-task [QA] (Jira)
├── Story 2 (Jira)
│   ├── Tech Note (Confluence)
│   └── Sub-tasks ...
└── ...
```

---

## Phases

### 1. Identify Origin

- Receive input: `{{PROJECT_KEY}}-XXX` (Jira key) or Confluence page ID
- `MCP: jira_get_issue(issue_key, fields="summary,status,issuetype,parent")`
- Determine artifact type: Epic / Story / Sub-task
- If Confluence page ID → `MCP: confluence_get_page(page_id)` → extract {{PROJECT_KEY}} keys → pivot to Jira
- **⛔ GATE — DO NOT PROCEED** without user confirmation of starting artifact + description of what changed.

### 2. Build Artifact Graph

Discovery algorithm:

```text
1. jira_get_issue(origin, fields="summary,status,issuetype,parent")
2. Walk UP:
   - if Sub-task → parent_story = issue.parent
   - if Story → parent_epic = issue.parent
   - if Sub-task → parent_epic = story.parent
3. Walk DOWN:
   - jira_search("parent = EPIC_KEY AND issuetype = Story", fields="summary,status,issuetype,parent") → stories
   - per story: jira_search("parent = STORY_KEY", fields="summary,status,assignee,issuetype") → sub-tasks
   ⚠️ NEVER add ORDER BY to parent queries — causes JQL parse error
4. Walk SIDEWAYS (Jira → Confluence):
   - per story: confluence_search("{{PROJECT_KEY}}-XXX") → Tech Note
   - epic: confluence_search(epic_title) → Epic Doc
```

**Token optimization:** fetch only `fields="summary,status,issuetype,parent"` (no description)

Output: inventory table (Type, Key/ID, Title, Status) for all discovered artifacts.

**🟡 REVIEW** — Present artifact graph + scope options. User selects: Full / Jira-only / Confluence-only / Selective. Proceed with user's selection.

### 3. Detect Changes

User describes changes, then classify:

| Change Type | Impact Level |
| --- | --- |
| Format only | LOW |
| Clarify wording | LOW |
| Add AC | MEDIUM |
| Modify AC | MEDIUM |
| Remove AC | HIGH |
| Change scope | HIGH |
| Technical detail change | MEDIUM |
| Business value change | HIGH |

**⛔ GATE — DO NOT PROCEED** without user confirmation of change classification.

### 4. Impact Analysis

Map changes → affected artifacts table (Artifact, Impact, Reason).

Impact types: `ORIGIN` (starting point) / `UPDATE` (will sync) / `FLAG` (review only) / `NO CHANGE`
Directions: DOWN (parent→child) / UP (child→parent) / SIDEWAYS (Jira↔Confluence)

**🟡 REVIEW** — Present impact table + sync plan to user. Proceed unless user objects.

### 5. Codebase Exploration (conditional)

> **🟢 AUTO** — Run only if scope changed or new file paths needed. Skip if format-only. Validate paths with Glob.

- Run only when: scope changed / need new file paths / new sub-task needed
- [Parallel Explore](../../../references/workflow-patterns.md#parallel-explore): Launch 2-3 agents (Backend/Frontend/Shared) IN PARALLEL.
- **Skip** if format-only / wording-only / technical detail change. Validate paths with Glob. Generic paths REJECTED.

### 6. Generate Sync Updates

Fetch full description only for artifacts with impact = UPDATE:

**Per Jira issue:**

- `MCP: jira_get_issue(issue_key, fields="summary,description")`
- Generate ADF JSON → `{{artifacts_dir}}/sync-bep-xxx.json`
- Show before/after comparison

**Per Confluence page:**

- `MCP: confluence_get_page(page_id)`
- If surgical (text replace) → prepare find/replace pairs
- If section update → generate new markdown section
- If full rewrite → generate full content → `{{artifacts_dir}}/sync-page-xxx.md`

**⛔ GATE — DO NOT EXECUTE** any sync without user approval of ALL generated updates.

### 7. Execute Sync

> **🟢 AUTO** — QG check → execute in order → cache invalidate. Escalate only on failure.
> HR1: Score all Jira ADF updates before execution. QG ≥ 90% required.

**QG Pre-check:** Score all Jira ADF updates against `shared-references/verification-checklist.md`. If < 90% → auto-fix → re-score (max 2). Escalate if still failing.

Order: Parents first → Children → Confluence

**Tool selection:**

| Change Type | Jira Tool | Confluence Tool |
| --- | --- | --- |
| Rewrite description | `acli --from-json` (ADF) | `create_confluence_page.py --page-id` |
| Text replacement | `update_jira_description.py` (surgical) | `update_confluence_page.py --find --replace` |
| Fields only | MCP `jira_update_issue` | — |
| Code blocks/macros | — | `update_page_storage.py` |

File pattern: `{{artifacts_dir}}/sync-bep-{type}.json` (Jira) / `{{artifacts_dir}}/sync-page-xxx.md` (Confluence)

> **🟢 AUTO** — HR6: `cache_invalidate(issue_key)` after EVERY Atlassian write.
> **🟢 AUTO** — HR3: If assignee needed, use `acli jira workitem assign -k "KEY" -a "email" -y` (never MCP).
> **🟢 AUTO** — HR4: Confluence pages with macros → use `update_page_storage.py` (never MCP).
> **🟢 AUTO** — HR5: New subtasks must use Two-Step + Verify Parent.

### 8. Verify & Report

> **🟢 AUTO** — Verify all artifacts automatically. Report results.

Verify with `audit_confluence_pages.py --config {{artifacts_dir}}/sync-audit.json`

Output: Summary table (Artifact, Action, Status) + flagged items for review.

Post-sync: `rm {{artifacts_dir}}/sync-*.json {{artifacts_dir}}/sync-*.md` → `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks`

---

## Edge Cases

> See [references/edge-cases.md](references/edge-cases.md) for edge case handling reference.

---

## When to Use

> See [references/decision-guide.md](references/decision-guide.md) for when to use this skill vs alternatives.

---

## Examples

### ✅ Good

```text
/sync-artifacts {{PROJECT_KEY}}-123 "AC3 updated — added rate limit constraint: max 3 redemptions per user"
# origin story key + precise change description → Phase 3 classifies as MEDIUM, cascades to subtasks + Confluence Tech Note

/sync-artifacts {{PROJECT_KEY}}-10 "epic scope narrowed: removed loyalty points integration from must-have list"
# epic key + scope change → HIGH impact, cascades DOWN to all child stories and subtasks

/sync-artifacts 98765432 "updated API response schema in Tech Note — added pagination fields"
# Confluence page ID → Phase 1 pivots to Jira via embedded {{PROJECT_KEY}} keys, syncs affected subtask descriptions

/sync-artifacts {{PROJECT_KEY}}-456 "fix typo in AC2 wording, no logic change"
# LOW impact change → Phase 5 codebase exploration skipped automatically, only wording updated
```

### ❌ Bad

```text
/sync-artifacts {{PROJECT_KEY}}-123                          # missing change description → Phase 1 gate blocks; agent cannot classify or plan sync
/sync-artifacts                                   # no origin artifact → Phase 1 cannot build artifact graph at all
/sync-artifacts {{PROJECT_KEY}}-123 "update description"     # too vague → Phase 3 cannot determine impact level or which artifacts to update
/sync-artifacts {{PROJECT_KEY}}-123 "fix AC"                 # use /verify-issue {{PROJECT_KEY}}-123 --fix instead — sync-artifacts is for cascading changes, not single-issue fixes
```

**Common mistakes:**

- Using `/sync-artifacts` for a single issue update — if only one issue needs editing, use `/verify-issue --fix` or `acli` directly; sync-artifacts is designed for cascading changes across the full artifact graph.
- Omitting the change description from the argument — Phase 1 has a hard gate that requires knowing what changed before building the artifact graph; without it the skill stops immediately.
- Providing a vague change description like "update" or "fix things" — Phase 3 change classification cannot determine impact level (LOW/MEDIUM/HIGH), so the sync plan will be over- or under-scoped.
- Forgetting that Confluence page IDs (not page titles) are the correct identifier — passing a page title causes Phase 1 to fail when pivoting to Jira.

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Templates Index](../../../references/templates.md) - Load by issue type (epic, story, subtask, task)
- [Tool Selection](../../../references/tools.md)
- [Verification Checklist](../../../references/verification-checklist.md)
- [Atlassian Scripts](../../../skills/utilities/atlassian-scripts/SKILL.md)
- [Edge Cases](references/edge-cases.md) - Edge case handling reference
- [Decision Guide](references/decision-guide.md) - When to use this skill vs alternatives
