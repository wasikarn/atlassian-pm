## 🎓 Domain Expert Notes

### Why This Approach

Task updates happen at two distinct moments with different risk profiles: pre-sprint (safe, no velocity impact) and in-sprint (risky, may invalidate sprint commitment). The preserve-intent phase makes scope change explicit and forces a conscious decision rather than a silent edit that corrupts sprint reporting.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Kanban Change Management (Anderson, 2010) | Phase 2 change type classification (migrate/add-details/change-type/update-content) | Anderson's explicit policies principle: classify changes by WIP impact before executing. `migrate` = standard change (zero WIP impact, pre-approved); `add-details` = low impact (additive, no scope shift); `change-type`/`update-content` = normal change (requires approval, WIP risk) |
| ITIL 4 Change Enablement | Phase 4 gate before applying changes | ITIL 4 defines 4 change types: **standard** (pre-approved, low risk) = migrate/add-details; **normal** (approval required, risk assessed) = update-content with scope shift; **emergency** (expedited, documented post-hoc) = blocked escalation path; **undoable** (irreversible) = type-change operations. The Phase 4 gate classifies every update against this taxonomy before applying |
| Agile Impediment Escalation (Scrum Guide) | Blocked task protocol in update-content changes | A task update that adds "blocked by" context triggers an impediment — must be visible to the Scrum Master within the same sprint day; description update alone is invisible on sprint board status filters |
| Docs as Code (Anne Gentle, "Docs Like Code", 2017) | Format migration (Wiki → ADF) change type | Treating task descriptions as versioned, structured documents reviewed with the same rigour as source code. ADF enforces structure; QG scoring provides the equivalent of a code review gate — ensures docs remain machine-readable and diffable |

### Key Metrics

- **Update-to-Creation Ratio:** Number of task updates vs. tasks created in a sprint — ratio > 0.5 signals tasks are being created before enough information is known
- **Format Debt:** Count of tasks still in Wiki markup (non-ADF) — migrate tasks reduce this debt; should trend to 0 over 2 sprints
- **Post-update QG Score:** QG score after each update — must not drop below the pre-update score; a drop signals content was degraded
- **Blocked Task Age:** Time a task spends in "blocked" state before being escalated — target < 1 business day; > 2 days signals impediment management gap

### Expert Decision Criteria

**Change type selection:**

- Task description uses Wiki markup (e.g., `*bold*`, `{code}`) → `migrate`; all other change types require ADF-format task first
- User wants to add more issues, ACs, or reference links to existing content → `add-details`; original content is never modified
- Task was created as `tech-debt` but the work is actually mechanical maintenance → `change-type` to `chore`; review ACs and checklist for consistency
- Specific sections have outdated information (stale PR link, changed file path) → `update-content`; only named sections change

**Blocked task escalation protocol:**

- If updating a task to add "blocked" status: record the blocker in the description AND transition the issue to "Blocked" in Jira
- Escalation path: developer → Tech Lead (same day) → Sprint Planning (next sprint if unresolved)
- A task that has been blocked for > 3 days without resolution should be removed from the sprint and re-planned

**Task handoff best practices:**

- When updating a task to change assignee (mid-sprint handoff): add a "Progress Note" section to the description with what was completed, what remains, and any gotchas discovered
- Handoff without a progress note = knowledge loss; the next developer will repeat investigation already done

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Task type changed but template structure not updated | `change-type` applied without regenerating the ADF template | Always regenerate full ADF template for the new type; do not patch old template sections |
| QG score drops after update | Sections removed or content degraded during "update-content" change | Run before/after QG comparison; if score drops, restore removed sections and re-score |
| Format migration breaks existing ADF panels | Wiki → ADF migration applied to an already-ADF task | Check current format in Phase 1 (`Identify current format`); never apply migration to ADF-format task |
| Blocked task not visible to Scrum Master | Task description updated but Jira status not transitioned | Pair description update with status transition to "Blocked"; description alone is invisible in sprint board filters |
| `/update-task` run on a Story key | No type-check in Phase 1; story updated as if it were a task | Check `issuetype` in Phase 1; if Story, redirect to `/update-story` immediately |

### Authoritative References

- **Mike Cohn — "Agile Estimating and Planning":** Task granularity and sprint commitment — tasks updated mid-sprint must be reviewed for capacity impact; the Phase 4 gate implements this discipline
- **David Anderson — "Kanban" (2010):** Explicit policies and change management — classifying changes before applying them is a core Kanban practice that prevents invisible scope creep
- **Jeff Sutherland — "Scrum: The Art of Doing Twice the Work in Half the Time":** Impediment removal is the Scrum Master's primary job — surfacing blocked tasks via status transition (not just description update) ensures impediments are visible
- **ITIL 4 Service Management:** Change enablement — the four change types (standard/normal/emergency/undoable) map directly to the four update-task change types in terms of risk profile and approval requirements
