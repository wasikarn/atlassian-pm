## 🎓 Domain Expert Notes

### Why This Approach

In-sprint subtask updates are high-risk changes: a subtask that shifts scope mid-sprint can invalidate the parent story's burndown, break date alignment with siblings, and silently corrupt sprint velocity metrics. The preserve-intent phase is the formal safeguard that separates _enriching_ a subtask (allowed) from _re-scoping_ it (requires story-level re-planning).

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Scrum Sprint Scope Protection (Scrum Guide) | Phase 3 Preserve Intent rules | Sprint commitment is inviolable; updating format/language is safe, but changing objective requires PO/TL sign-off. The Scrum Guide (2020) states: "Sprint scope may be clarified and renegotiated with the Product Owner as more is learned" — clarification is safe, renegotiation is not a silent edit |
| Earned Value Management — ANSI/EIA-748 | HR8 date validation in Phase 6 | Subtask dates must stay within parent range to preserve schedule baseline integrity. ANSI/EIA-748 defines the "rubber baseline" anti-pattern: when dates shift continuously, EV calculations become meaningless. HR8 prevents this at the subtask level |
| WIP Limit Discipline — Cost of Change (Anderson, Ch.5) | Phase 2 change type identification | Anderson: every in-sprint scope expansion increases active WIP, and **cost of change = WIP × lead time impact**. If current WIP = 3 parallel subtasks, a scope change ripples across all 3 streams simultaneously. Classify before applying to make WIP cost explicit |
| Impediment Management (Scrum Guide) | Content updates that add "blocked by" or remove ACs | Removals and dependency additions must be flagged to the Scrum Master, not silently applied. The Scrum Guide defines impediments as anything preventing the Developers from achieving the Sprint Goal — a blocked subtask qualifies and must surface on the board, not just in the description |

### Key Metrics

- **In-sprint Update Frequency:** Number of subtask updates after sprint start — > 2 updates per subtask signals poor initial decomposition; review story-to-subtask breakdown
- **Scope Drift Rate:** % of subtasks where objective changed mid-sprint — target 0%; any objective change should trigger a sprint re-planning discussion
- **Date Alignment Violations (HR8):** Count of subtasks with dates outside parent range — must be 0; violations corrupt sprint burndown charts
- **Description Completeness Score:** QG score before and after update — update should not decrease QG score; if it does, the update introduced ambiguity

### Expert Decision Criteria

**When an update is safe (no re-planning needed):**

- Format migration (Wiki → ADF): zero content change, always safe
- Language translation (EN → Thai + transliteration): preserves meaning, always safe
- Adding file paths discovered via `Task(Explore)`: adds specificity, does not change scope
- Fixing typos or broken links: always safe

**When an update requires TL/PO approval first:**

- Adding new ACs to a subtask already In Progress — expands scope, may delay completion
- Removing existing ACs from a subtask — signals scope reduction; must check if the removed AC is covered elsewhere
- Changing estimated hours (OE field) mid-sprint — affects sprint capacity model and velocity reporting
- Changing the subtask objective (what it delivers) — this is a new subtask, not an update

**Date update rules (HR8 enforcement):**

- Subtask `start_date` must be ≥ parent story `start_date`
- Subtask `due_date` must be ≤ parent story `due_date`
- If new dates violate the parent range, update the parent story's dates first, then apply subtask dates

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Sprint burndown shows subtask "done" but story still open | Subtask scope expanded without updating parent story ACs | Phase 3: check if added ACs are covered in parent story; if not, update story first |
| Subtask dates drift outside parent range after update | HR8 validation skipped or parent dates not fetched in Phase 1 | Always fetch parent dates in Phase 1; validate after every date field change in Phase 6 |
| Subtask sprint field set directly (API error) | HR10 not enforced; user explicitly requests sprint assignment | Refuse: sprint is always inherited from parent; direct setting causes API error and cascade failure |
| ACs silently removed during format migration | Phase 3 preservation not applied to checklist items | Count ACs before and after generation; if count differs, flag to user before applying |
| Updated subtask fails QG after apply | Content was modified beyond stated change type in Phase 2 | Re-run QG; if < 90%, auto-fix then re-score before accepting the update as complete |

### Authoritative References

- **Scrum Guide (Schwaber & Sutherland):** Sprint goal and scope protection — the preserve-intent rules directly implement the Scrum principle that sprint scope is agreed at planning and only changed by mutual consent
- **Project Management Institute (PMI) — PMBOK:** Integrated Change Control — any scope change (even at subtask level) requires a change request; Phase 3 gate is the lightweight equivalent
- **Earned Value Management (ANSI/EIA-748):** Schedule baseline integrity — date validation (HR8) prevents "rubber baseline" syndrome where dates shift continuously, making EV metrics meaningless
- **Anderson, David J. — "Kanban" (2010):** WIP limits and change cost — mid-sprint scope changes add invisible WIP; the identify-changes phase makes the WIP cost visible before committing
