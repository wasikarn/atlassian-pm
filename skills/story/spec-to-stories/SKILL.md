---
name: spec-to-stories
disable-model-invocation: true
context: fork
x-compatibility: [jira-cache-server, mcp-atlassian, mcp-confluence, acli]
description: |
  Convert a Confluence spec/requirements page into Jira User Stories.
  Extracts personas, requirements, and AC hints via spec-parser-agent. Deduplicates against existing issues.
  --dry-run shows stories + QG scores without creating in Jira.
  Triggers: "spec to stories", "import requirements", "convert spec", "requirements to stories", "แปลง spec"
argument-hint: "<confluence-page-id> [--epic <key>] [--dry-run]"
---

# /spec-to-stories

**Role:** PO — Requirements Ingestion
**Output:** Jira User Stories created from Confluence spec + coverage map

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`

## Context Object

| Phase | Adds to Context |
|-------|----------------|
| 1. Fetch | `page_content`, `page_title` |
| 2. Extract | `sections[]`, `requirements[]`, `personas[]`, `constraints[]` |
| 3. Map | `story_drafts[]` (narrative + ACs per requirement group) |
| 4. Dedup | `dedup_flags[]` (stories flagged as likely duplicate) |
| 5. Review | `approved_stories[]` |
| 6. QG | `qg_results[]` |
| 7. Created | `story_keys[]`, `coverage_map{}` |

> **Workflow Patterns:** See [workflow-patterns.md](../../../references/workflow-patterns.md)

## Phase 1 — Fetch Spec

`confluence_get_page(page_id)` — full page with body content.

If `--epic` provided: fetch `cache_get_issue(epic_key)` to understand scope context.

Display: "Fetched: [page_title] ([word_count] words)"

## Phase 2 — Extract Requirements

`Agent(name: "spec-parser-agent"): page_content`

Display extraction summary:

- Sections: [N] found
- Requirements: [N] extracted (functional: X, non-functional: Y)
- Personas: [list]
- Constraints: [list]

## Phase 3 — Map to Stories

Group requirements by persona + feature area into story clusters.

For each cluster → draft User Story:

- **Narrative:** "As a [persona], I want to [goal], so that [benefit]"
- **ACs:** Given/When/Then per requirement in cluster (minimum 1 happy path + 1 error case)
- **Scope:** services impacted from requirement context
- **VS label:** suggest from feature area name
- **SP estimate:** S/M/L based on requirement count + complexity hints

## Phase 4 — Dedup Check

For each story draft: `cache_similar_issues(text=narrative+acs, limit=3)`

Flag if similarity score **> 0.8**:

```
⚠ Story [N] may duplicate {{PROJECT_KEY}}-123 (similarity: 0.87): "[existing summary]"
```

## Phase 5 — Review Stories

🔄 ITERATE (max 3 rounds): Display all story drafts with ACs + dedup flags.

Ask: "Review complete? (annotate stories to modify, or approve all)"

If `--dry-run`: output QG scores and stop here — do NOT create in Jira.

## Phase 6 — QG Batch

Score each approved story against verification-checklist.md:

- Technical T1-T5
- Story Quality S1-S6

Report: "Story [N]: Technical X/5 | Story Quality X/6 | Overall X%"

If any story < 90%: auto-fix (max 2 attempts), then re-score. Still < 90% → ask user.

## Phase 7 — Batch Create

**⛔ GATE** — Show final story count + epic link before creating.

1. `jira_batch_create_issues` — all approved stories with parent epic
2. HR5 batch pattern: create all → verify all parents → `acli` edit all descriptions
   - Verify: `jira_get_issue(key, fields="parent")` per story → confirm `parent.key = epic_key`
   - If parent missing: re-add via `python3 scripts/api/jira_set_parent.py --issues KEY --parent EPIC`
3. HR6: `cache_invalidate(key)` for each created story

## Phase 8 — Summary

🟡 REVIEW: Display:

- Created: [N] stories
- Coverage map: spec section → story key(s)

  ```
  User Authentication → {{PROJECT_KEY}}-201, {{PROJECT_KEY}}-202
  Password Reset → {{PROJECT_KEY}}-203
  ```

- Next: run `/atlassian-pm:create-story {{PROJECT_KEY}}-XXX` per story to add subtasks

---

## Examples

### ✅ Good

```text
/spec-to-stories 98765432 --dry-run                     # preview extracted stories + QG scores before creating anything in Jira
/spec-to-stories 98765432 --epic {{PROJECT_KEY}}-10                 # link all generated stories to epic {{PROJECT_KEY}}-10; parent verified per HR5
/spec-to-stories 98765432 --epic {{PROJECT_KEY}}-10 --dry-run       # safest first run: validate story output + dedup flags before committing to Jira
```

### ❌ Bad

```text
/spec-to-stories                                         # no page ID → Phase 1 cannot fetch spec; skill cannot proceed
/spec-to-stories "User Authentication Spec"             # page title instead of page ID → confluence_get_page requires numeric ID, not title
/spec-to-stories 98765432                               # creating directly without --dry-run first — dedup flags and QG scores not reviewed before Jira write
/spec-to-stories 98765432 --epic {{PROJECT_KEY}}-10                 # page has no structured spec (e.g. meeting notes) → spec-parser-agent produces low-quality requirements; run /blueprint first to create a proper spec page
```

**Common mistakes:**

- Skipping `--dry-run` on the first run — always preview story output and check dedup flags (similarity > 0.8) before creating in Jira; retrofitting is much harder than preventing duplicates upfront.
- Passing a Confluence page title instead of its numeric page ID — `confluence_get_page` requires the ID; use the page URL or Confluence API to find it.
- Omitting `--epic` when stories should belong to an epic — stories will be created without a parent, requiring a separate `jira_set_parent.py` call to fix hierarchy.
- Running on an unstructured page (meeting notes, brainstorming docs) — `spec-parser-agent` needs clear sections with personas and requirements; use `/blueprint` to produce a proper spec page first.
