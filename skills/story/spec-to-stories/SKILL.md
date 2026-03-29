---
name: spec-to-stories
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, mcp-confluence, acli]
description: |
  Convert a Confluence spec/requirements page into Jira User Stories.
  Extracts personas, requirements, and AC hints via spec-parser-agent. Deduplicates against existing issues.
  --dry-run shows stories + QG scores without creating in Jira.
  Triggers: "spec to stories", "import requirements", "convert spec", "requirements to stories", "แปลง spec", "batch stories from spec"
  Use when: batch-converting a Confluence spec or requirements page into multiple User Stories with deduplication
  Do NOT use for: creating a single story (use create-story); updating existing stories (use update-story)
argument-hint: "<confluence-page-id> [--epic <key>] [--dry-run]"
effort: high
---

# /spec-to-stories

**Role:** PO — Requirements Ingestion
**Output:** Jira User Stories created from Confluence spec + coverage map

## Dynamic Context

- **Today:** !`date +%Y-%m-%d`
- **Team:** @.claude/project-config.json → `team.members[]`

## Context Object

| Phase | Adds to Context |
| ----- | --------------- |
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

```text
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

  ```text
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

## 🎓 Domain Expert Notes

### Why This Approach

Specification by Example (Gojko Adzic) establishes that requirements only become unambiguous when expressed as concrete, testable examples — not prose paragraphs. This skill operationalises that principle: the spec-parser-agent extracts structured requirements and immediately maps them to Given-When-Then scenarios, forcing the spec author's intent to surface as verifiable behaviors rather than interpretable statements.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Specification by Example (Gojko Adzic, 2011) | Phase 2 Extract → Phase 3 Map | Requirements expressed as examples (scenarios) are unambiguous and directly drive test automation; prose requirements require an extra translation step that introduces drift |
| User Story Mapping (Jeff Patton) | Phase 3 grouping by persona + feature area | Patton's backbone → activities → tasks hierarchy maps to: Persona → Feature Area → Story cluster; this grouping prevents persona-crossing stories |
| Feature Injection (Chris Matts) | Phase 2 persona + constraint extraction | "In order to [goal], As a [persona], I want [feature]" — Feature Injection starts from goals, not from system features; ensures extracted stories anchor to real user needs |
| BDD Given-When-Then (Dan North) | Phase 3 AC format per requirement | Minimum 1 happy path + 1 error case per requirement cluster; this satisfies the "Testable" criterion without requiring full test case design at story-creation time |
| Semantic dedup (cosine similarity thresholds) | Phase 4 Dedup Check | Two-tier threshold for English+Thai mixed-language backlogs: similarity **> 0.8** = likely duplicate → auto-flag, require confirmation before creating; similarity **0.7–0.8** = borderline → show candidate to user for manual decision, do not auto-flag or auto-skip. Below 0.7 = distinct enough to proceed without review |

### Key Metrics

- **Extraction yield:** Target 1 story per 3-5 requirements; lower ratio suggests over-granular stories; higher ratio suggests under-specified requirements needing `/blueprint` first
- **Dedup flag rate:** > 30% of stories flagged as duplicates indicates the spec page overlaps significantly with existing backlog — consolidate or update existing stories instead
- **QG batch pass rate:** < 70% of stories passing QG on first attempt indicates the spec lacks sufficient persona and scenario detail for automatic extraction to work well
- **Coverage map completeness:** Every spec section must appear in the coverage map output; unmapped sections indicate requirements that were dropped during extraction and need manual review

### Expert Decision Criteria

- If the spec page contains more than one persona and they have conflicting workflows → create separate story clusters per persona rather than merging them; mixed-persona stories fail INVEST Independent
- If a requirement group yields more than 7 ACs → split into two stories along the happy-path vs. edge-case boundary; one story for the primary flow, one for error/boundary handling
- If dedup similarity is between 0.7-0.8 (borderline) → show the candidate duplicate to the user before proceeding; do not auto-flag or auto-skip
- If `--dry-run` QG scores average below 70% → do not proceed to Phase 7 batch create; return to the spec page and enrich persona/scenario detail or run `/blueprint` to rewrite the spec
- Non-functional requirements (performance, security, accessibility) extracted from the spec → convert to explicit ACs on the relevant functional story, not separate stories, unless they require independent implementation work

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Stories created as orphans (no epic) | `--epic` omitted or epic key typo | Run `jira_set_parent.py --issues KEY1,KEY2 --parent EPIC`; verify with `jira_get_issue(fields="parent")` per story |
| spec-parser-agent produces low-quality requirements | Source page is meeting notes or brainstorm, not a structured spec | Run `/blueprint <confluence-page-id>` first to produce a spec with explicit personas, requirements, and constraints sections |
| Duplicate stories created despite dedup flag | User approved flagged story without reviewing the existing issue | Before approving flagged stories, use `cache_get_issue` to read the candidate duplicate; update the existing story instead if scope overlaps |
| Story narrative reads as a feature description ("The system will support X") | Feature Injection not applied — spec written from system-out rather than user-in | Rewrite narrative using the persona identified in Phase 2: "As a [persona], I want [goal] so that [value]" |
| Coverage map has unmapped spec sections | spec-parser-agent skipped sections with no persona signal | Manually review unmapped sections; add a catch-all story or annotate the spec page to indicate intentionally deferred scope |

### Authoritative References

- **Gojko Adzic, "Specification by Example" (2011):** "Key examples are not test cases — they are a communication tool that becomes the acceptance test"; the spec-parser-agent extracts these key examples from prose requirements
- **Jeff Patton, "User Story Mapping" (2014):** "Don't just break down stories — map the whole journey first"; the persona + feature area grouping in Phase 3 is the lightweight version of Patton's backbone construction
- **Chris Matts (Feature Injection):** Goals before features — if the spec doesn't state a user goal for a requirement, the extracted story will lack the "Valuable" INVEST criterion
- **Dan North (BDD, 2006):** "The scenario title should describe a role and an action"; Phase 3's `AC{N}: [Verb] — [Scenario Name]` format directly implements this naming convention

---

## References

- [ADF Core Rules](../../../references/templates-core.md) - CREATE/EDIT rules, panels, styling
- [Story Template](../../../references/templates-story.md) - Story ADF template + best practices
- [Writing Style](../../../references/writing-style.md) - Thai + transliteration conventions
- [Verification Checklist](../../../references/verification-checklist.md) - INVEST criteria, quality checks
