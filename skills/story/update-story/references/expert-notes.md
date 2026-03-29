## 🎓 Domain Expert Notes

### Why This Approach

Story updates during a sprint are the single largest source of mid-sprint scope creep in agile teams (Atlassian State of Agile 2024). The Preserve Intent phase exists because story changes are rarely neutral: adding an AC almost always implies new subtask work, and removing an AC almost always implies a subtask that is now doing work the team agreed to descope. Making the impact explicit before generating the update prevents silent misalignment between the story and its child artifacts.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Definition of Ready re-validation (DoR) | Phase 5 Quality Gate | Any change that affects scope, ACs, or value proposition resets the DoR clock; the 90% QG threshold is the automated DoR re-check |
| Change Impact Matrix | Phase 2 Impact Analysis table | Maps change type → subtask/QA impact; industry-standard practice from ITIL change management adapted to story-level granularity |
| Preserve Intent principle (Ron Jeffries) | Phase 3 Preserve Intent rules | The story's core value proposition (the "So that" clause) must remain stable across updates; changes to value proposition require a new story or epic-level re-scoping discussion |
| HR8 Date Alignment | Phase 6 subtask date fix | Parent date changes cascade to children; failing to propagate date changes creates HR8 violations that corrupt sprint burndown and capacity reports |
| Scope creep taxonomy | Phase 2 change type classification | Distinguishes between legitimate refinement (add AC that was always implied) and scope creep (add AC that expands the original commitment); only the former should be processed without escalation |

### Key Metrics

- **Change frequency threshold:** If a story requires more than 2 update cycles in a single sprint, it is a signal that the story was not sufficiently refined before sprint start (DoR failure upstream)
- **AC delta limit:** Adding or removing more than 2 ACs in a single update is a HIGH-impact change that should trigger `/sync-artifacts` rather than `/update-story`; the impact graph is too wide for single-story update
- **Subtask alignment rate:** After any AC change, 100% of active (not Done) subtasks must be re-checked for relevance; Done subtasks are flagged only, never modified
- **QG re-pass rate:** If QG fails after 2 auto-fix attempts on an update, the update is structurally inconsistent — return to Phase 2 and re-classify the change type

### Expert Decision Criteria

- If the change removes an AC that a subtask exclusively covers → do NOT delete the subtask silently; flag it for the assignee and surface a "descope decision" to the user before applying the update
- If the story is `In Progress` (sprint active) and the change type is HIGH (Remove AC, Change scope) → escalate to the user with an explicit sprint impact warning before proceeding; mid-sprint scope reduction affects team velocity metrics
- If `start_date` or `due_date` changes → always run HR8 subtask alignment; never skip even if the user says "just update the story dates"; date misalignment silently corrupts sprint burndown
- If change type is "Format only" → skip Phases 2-3 entirely; go directly to Phase 4 Generate Update with a format-migration template; QG must still pass
- If the story narrative's persona changes → this is a HIGH-impact change equivalent to "Business value change"; the story may no longer fit its parent epic scope — run A4 alignment check from `/verify-issue` before applying

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Subtask still covers descoped AC after story update | Phase 2 subtask impact analysis skipped or dismissed | Fetch all subtasks post-update via `jira_search(jql="parent={{PROJECT_KEY}}-XXX")`; compare each subtask objective against current story ACs; flag orphaned subtasks |
| Story QG fails after adding a well-written AC | New AC uses implementation language ("Implement X") instead of outcome language ("User sees X") | Rewrite AC using Given-When-Then outcome format; implementation ACs consistently fail the Testable criterion |
| Date update causes HR8 violation | Subtask dates not adjusted after parent date shift | Run `sprint_subtask_alignment.py --sprint <id>` immediately after any parent date change; verify with `jira_get_issue(fields="{{START_DATE_FIELD}},duedate")` per subtask |
| Update applied but cache returns stale data | HR6 `cache_invalidate` not called after `acli` write | Call `cache_invalidate(issue_key)` immediately after every write; verify with `cache_get_issue` that the summary/description reflects the change |
| "Preserve Intent" rule prevents a legitimate redesign | Story has fundamentally changed in scope but `/update-story` is being used instead of creating a new story | If the "So that" benefit clause changes, close the current story and create a new one via `/create-story`; don't patch a misaligned story |

### Authoritative References

- **Atlassian, "Definition of Ready" (2024):** "Review your DoR regularly — if you notice the team is regularly not completing all their work in a sprint, it likely means your DoR needs to be reviewed"; story updates that bypass the QG re-check are the most common DoR evasion
- **Mike Cohn, "Agile Estimating and Planning" (2005):** Scope changes during a sprint should be logged as new backlog items and traded against existing items of equal size; silent in-sprint AC additions are the most common cause of sprint overcommitment
- **Ron Jeffries (XP):** "A story's value proposition is the contract with the customer — changing it mid-sprint without discussion is a contract breach"; the Preserve Intent phase formalises this boundary
- **DEEP Backlog criteria (Mike Cohn):** Detailed Appropriately, Estimated, Emergent, Prioritised — the "Emergent" criterion explicitly allows story evolution; the key is that evolution is conscious and impact-assessed, not accidental

---
