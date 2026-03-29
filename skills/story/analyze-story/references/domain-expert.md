## 🎓 Domain Expert Notes

### Why This Approach

Technical analysis works backward from user value: first establish what the story delivers end-to-end (vertical slice), then decompose into the minimum number of service-boundary subtasks that together produce that value. Forcing codebase exploration before design prevents subtasks from being written to abstract layers rather than real implementation paths.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Vertical Slicing (Mike Cohn) | Phase 2 VS Verification, Phase 4 VS Integrity | Ensures every subtask contributes to shippable value; avoids horizontal layer-only work that never independently ships |
| T-Shirt Sizing → Story Points | Phase 4 subtask OE (Original Estimate) | High-level sizing first (S/M/L) establishes confidence intervals before committing to hour estimates |
| Planning Poker consensus model | Phase 4 ITERATE annotation cycle | Subtask-level estimates require team discussion; single-expert estimates have 30-40% higher variance |
| Dependency Ordering (Critical Path) | Phase 4 Tech Lead decomposition | Data layer → Auth → API → Service → FE Service → FE Component mirrors real build dependency graph; violating this order causes blocked sprints |
| Event Storming (light) | Phase 2 Event Flow table | Command/Event/Consumer mapping surfaces cross-service side effects before subtask boundaries are drawn |

### Key Metrics

- **Subtask count per story:** Target 3-6 subtasks; fewer than 3 suggests under-decomposition or layer-only slice; more than 7 indicates the parent story may be too large (violates INVEST Small)
- **Codebase exploration coverage:** Every service marked "impacted" in Phase 2 must have at least one real file path discovered in Phase 3; zero file paths = blocked QG
- **Estimation variance threshold:** If subtask OE sum deviates more than 40% from parent SP equivalent (1 SP ≈ 4h), flag for re-estimation before creation
- **AC-to-subtask coverage ratio:** Each story AC must be traceable to at least one subtask objective; unmapped ACs indicate scope gaps caught in Alignment Check (Phase 5)

### Expert Decision Criteria

- If a subtask covers more than one service boundary → split it; cross-service subtasks create ambiguous ownership and blur burndown attribution
- If Phase 3 exploration returns only generic paths (e.g. `src/controllers/`) → reject and re-explore; generic paths produce generic ACs that fail QG
- If the Event Flow table (Phase 2) shows a consumer in a service NOT listed in the Impact table → add that service to the impact table before proceeding to Phase 3
- If story is in `In Progress` status when `/analyze-story` is called → verify no subtasks already exist (`/verify-issue --with-subtasks`) before creating new ones; duplicate subtask creation is the most common misuse of this skill
- Technical debt subtasks (refactoring, migration) should be explicitly labeled and estimated separately from feature subtasks — mixing them inflates velocity metrics

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| QG rejects subtask file paths | Phase 3 exploration used `find` or generic glob instead of `ast-grep` or service-specific paths | Re-run exploration using module-level paths; validate each path with Glob before designing ACs |
| Parent verify (HR5) fails silently | MCP `jira_create_issue` accepted the call but ignored the `parent` field | Always use Two-Step: create shell → `jira_get_issue(fields="parent")` → if missing, fix via `jira_set_parent.py` before continuing |
| Subtask sum SP >> parent SP | Phase 4 decomposed at task granularity rather than service-boundary granularity | Merge subtasks that belong to the same service; aim for 1 subtask per service unless complexity clearly justifies a split |
| Subtasks don't cover all story ACs | Phase 4 subtask design referenced the story narrative but not each individual AC | Go through ACs one by one in Phase 4; each AC must appear in at least one subtask objective |
| Sprint burndown shows subtask work not decreasing | Subtask dates fall outside parent date range (HR8 violation) | Run `sprint_subtask_alignment.py` to redistribute dates within parent range |

### Authoritative References

- **Mike Cohn, "User Stories Applied" (2004):** Vertical slices must deliver a thin, complete, testable capability — "a story is not a task, it is a promise of a conversation"
- **Jeff Patton, "User Story Mapping" (2014):** Decompose from user journey activities → backbone tasks → subtasks; never decompose from technical layer first
- **Atlassian Engineering Blog:** Subtask granularity sweet spot is 4-8h per subtask; below 2h indicates over-decomposition that inflates ceremony overhead
- **Daniel Vacanti, "Actionable Agile Metrics" (2015):** Work items that cross service boundaries have 2-3x higher cycle time variability — minimize cross-service subtasks
