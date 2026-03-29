---
name: search-issues
context: fork
agent: Explore
model: haiku
effort: low
x-compatibility: [atlassian-cache, mcp-atlassian]
allowed-tools: Read, Glob, Grep, Bash, Agent, mcp__mcp-atlassian__jira_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_text_search, mcp__plugin_atlassian-pm_atlassian-cache__cache_similar_issues
description: |
  Search for existing Jira issues to prevent duplicates — invoke proactively whenever the user
  wants to create any new issue (story/task/epic/subtask) before they start creating.
  3-phase workflow with JQL + semantic similarity check.

  Supports: keyword search, JQL query, issue key, filters (sprint, assignee, status, type)

  Triggers: "search", "find", "find issue", "does it already exist", "look for", "check if exists",
  "before creating", "is there already", "find related", "search sprint", "search backlog",
  "any similar issues", "ค้นหา", "มี issue อยู่แล้วไหม"
  Use when: searching Jira for existing issues before creating new ones to prevent duplicates
  Do NOT use for: creating issues (use create-story or create-task); full backlog analysis (use scan-tech-debt)
argument-hint: "[keyword] [--filters]"
---

# /search-issues

**Role:** Any
**Output:** List of matching issues

## Phases

### 1. Parse Search Criteria

| Input | Generated JQL |
| --- | --- |
| `"credit"` | `project = {{PROJECT_KEY}} AND summary ~ "credit"` |
| `ABC-123` | `key = ABC-123` |
| `ABC-123 --children` | `parent = ABC-123` |
| `--sprint current` | `sprint IN openSprints()` |
| `--assignee me` | `assignee = currentUser()` |
| `--status "In Progress"` | `status = "In Progress"` |
| `--type Story` | `type = Story` |

### 2. Execute Search

```text
MCP: jira_search(jql: "[generated JQL]", fields: "summary,status,assignee,issuetype,priority", limit: 20)
```

### 2.5 Semantic Similarity Check (keyword search only)

**Skip if:** input is issue key (`ABC-123`), uses `--jql`, or uses `--children` flag.

```text
cache_similar_issues(query: "<keyword>", limit: 5, exclude_keys: [<keys from Phase 2>])
```

Filter results by distance (cosine distance, 0 = identical):

| Distance | Label | Action |
| --- | --- | --- |
| < 0.25 | ⚠️ Likely duplicate | แจ้งเตือนชัดเจน |
| 0.25–0.45 | 🔍 Possibly related | แสดงไว้อ้างอิง |
| > 0.45 | (skip) | noise — ไม่แสดง |

Similarity % = `(1 - distance/2) × 100`

If embeddings not available (sqlite-vec not installed) → skip gracefully, no error.

### 3. Display Results

```text
## Search Results
Query: `project = {{PROJECT_KEY}} AND summary ~ "credit"`
Found: 5 issues

| Key | Type | Summary | Status |
|-----|------|---------|--------|
| ABC-123 | Story | Credit feature | In Progress |
| ABC-124 | Sub-task | [BE] Credit API | To Do |

## 🔍 Semantic Matches (BERT similarity)
| Key | Summary | Similarity |
|-----|---------|------------|
| ABC-120 | [BE] เติมเครดิต wallet | ⚠️ 94% (likely duplicate) |
| ABC-118 | Credit payment flow | 🔍 72% (possibly related) |

💡 พบ likely duplicate → ยืนยันก่อนสร้าง issue ใหม่
```

If no semantic matches above threshold → omit the section entirely.

---

## Filter Options

| Flag | Example |
| --- | --- |
| `--sprint` | `--sprint current`, `--sprint "Sprint 5"` |
| `--assignee` | `--assignee me` |
| `--status` | `--status "In Progress"` |
| `--type` | `--type Story` |
| `--label` | `--label BE` |
| `--children` | `ABC-XXX --children` |
| `--jql` | `--jql "custom query"` |

---

## Use Cases

> See [references/use-cases.md](references/use-cases.md) for example commands by use case.

---

## Examples

### ✅ Good

```text
/search-issues "credit wallet"                          # keyword search + semantic similarity check
/search-issues {{PROJECT_KEY}}-42 --children                        # list all subtasks of a parent issue
/search-issues --sprint current --assignee me           # my open items in active sprint
/search-issues --type Story --status "In Progress"      # filter by type + status
/search-issues --jql "labels = tech-debt AND sprint IN openSprints()"   # custom JQL filter
```

### ❌ Bad

```text
/search-issues                                          # no query — produces empty or full-project dump
/search-issues --jql "parent = {{PROJECT_KEY}}-42 ORDER BY created"    # HR2 violation: ORDER BY with parent= causes JQL parser error
/search-issues "payment flow" --sprint current          # valid, but using this for sprint planning decisions —
                                                        # use /plan-sprint instead; search-issues only surfaces issues
/create-story "Add credit feature"                      # creating without running /search-issues first —
                                                        # skips duplicate check; may create redundant issue
```

**Common mistakes:**

- Using `ORDER BY` together with `parent =`, `parent in`, or `key in (...)` in a `--jql` query — this triggers a Jira JQL parser error (HR2); remove the `ORDER BY` clause
- Treating search results as a sprint planning tool — `/search-issues` surfaces issues but does not evaluate capacity or priority; use `/plan-sprint` for planning decisions
- Not running `/search-issues` before `/create-story` or `/create-task` — the semantic similarity check catches near-duplicates that exact JQL misses

---

## References

- [references/use-cases.md](references/use-cases.md) — example commands by use case
- [JQL Quick Reference](../../../references/jql-quick-ref.md)

---

## 🎓 Domain Expert Notes

### Why This Approach

Jira's JQL engine is an indexed database query — query structure determines execution time as much as data volume does. The skill's two-phase approach (JQL for structured filters + semantic similarity for near-duplicate detection) compensates for JQL's fundamental limitation: it matches exact tokens but misses synonyms, paraphrases, and bilingual equivalents. The combination catches duplicates that JQL alone would miss.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Indexed field preference | Phase 2 JQL generation | Atlassian's own JQL optimisation guide lists `project`, `issuetype`, `status`, `assignee`, `sprint` as indexed — leading with these fields allows the query planner to narrow results before scanning non-indexed fields like `labels` or `summary ~` |
| Semantic similarity (cosine distance) | Phase 2.5 duplicate detection | Cosine distance < 0.25 signals near-identical meaning across different phrasings or languages — catches Thai-language duplicates of English issues that exact JQL `summary ~` would miss entirely |
| Saved filters as building blocks | `--jql` escape hatch | Atlassian's dashboard design pattern: save atomic filters (e.g., "my open stories") and compose them — `--jql` in this skill is the composition layer |

### Key Metrics

- **Duplicate detection rate:** Percentage of new issue creates preceded by a `/search-issues` run — target 100%; skipping search is the primary driver of backlog duplication in Jira projects
- **Semantic threshold calibration:** Cosine distance < 0.25 = likely duplicate (flag for confirmation); 0.25–0.45 = possibly related (show as reference); > 0.45 = noise (suppress). These thresholds are tuned for English+Thai mixed-language backlogs
- **Query performance indicator:** If `jira_search` with `limit=20` takes >3s, the JQL is likely leading with a non-indexed field (`labels`, `summary ~`) — reorder clauses to put `project =` and `issuetype =` first

### Expert Decision Criteria

- Always lead JQL clauses with `project =` — this is the single highest-impact optimisation; it restricts the search space before any other filter is applied
- Use `sprint IN openSprints()` rather than hardcoded sprint IDs — dynamic functions keep saved filters valid across sprint boundaries without maintenance (HR7 principle applied to JQL)
- Avoid `ORDER BY` when using `parent =`, `parent in`, or `key in (...)` — this is a known Jira JQL parser error (HR2); sort results client-side if ordering is needed
- For dashboard filters, prefer `AND` within sub-clauses and `OR` at the top level — Atlassian's query planner handles top-level `OR` more efficiently than nested `AND/OR` combinations
- `labels` is a slow field — if filtering by label is required, combine it with `project =` and at least one indexed field first to limit the scan set
- Use relative date functions (`startOfWeek()`, `-7d`) instead of absolute dates in saved filters — absolute dates create stale filters that silently return wrong results after the date passes

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Search returns 0 results for a known existing issue | `summary ~` is case-sensitive for exact phrases with quotes | Remove quotes to use full-text search: `summary ~ "credit"` not `summary ~ "Credit System"` |
| JQL parser error on `parent =` with `ORDER BY` | HR2 violation — known Jira parser bug | Remove `ORDER BY` clause; issues are sorted by relevance by default |
| Semantic search returns no results | `sqlite-vec` not installed or embeddings not built | Skill degrades gracefully (Phase 2.5 skipped); run `cache_stats` to verify embedding availability |
| `--sprint current` returns issues from wrong sprint | Multiple open sprints on the board | Use `sprint IN openSprints()` which matches all active sprints, not just the first one |
| Saved `--jql` filter returns stale data | Hardcoded dates in the JQL expression | Replace absolute dates with `startOfWeek()`, `-14d`, or `startOfMonth()` |

### Authoritative References

- **Atlassian JQL Optimisation Guide (support.atlassian.com):** "Limiting the scope of queries by focusing on specific projects allows Jira to ignore unnecessary work items" — `project =` is the single most impactful clause
- **Atlassian Advanced JQL Tips (community.atlassian.com):** Use `AND` mostly in sub-clauses and reserve `OR` for main clauses — the query planner handles this structure most efficiently
- **Atlassian Jira Advanced Searching (support.atlassian.com):** Saved filters act as reusable query components; combining them with `AND`/`OR` avoids duplicating filter logic and keeps individual filters maintainable across sprint boundaries — the `--jql` flag in this skill is the composition mechanism for that pattern
