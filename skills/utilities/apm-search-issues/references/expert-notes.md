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
