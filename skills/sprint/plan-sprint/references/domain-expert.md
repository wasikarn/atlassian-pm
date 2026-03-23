## 🎓 Domain Expert Notes

### Why This Approach

The Scrum Guide 2020 defines Sprint Planning as answering three questions: Why is this Sprint valuable? What can be Done? How will the chosen work get done? This skill's 8-phase flow maps directly to those questions — capacity (Phase 2) answers "what can be Done," prioritization (Phase 4) answers "what is valuable," and distribution + risk (Phases 5-6) answer "how." Skipping any phase degrades the quality of the answer to its corresponding question.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Scrum Guide 2020 Sprint Planning | Phases 1-8 overall structure | The authoritative definition of what Sprint Planning must produce: a Sprint Goal + Sprint Backlog + execution plan |
| Yesterday's Weather (Scrum pattern) | Phase 2 — team velocity calculation | Plan at 80% of 3-sprint rolling average velocity; single-sprint data is noise; ±20% is the reliable precision band |
| Definition of Ready (DoR) | Phase 4 — story readiness validation | A PBI is ready for planning only when it has: clear acceptance criteria, estimated size, no unresolved dependencies, and approved design/mockups; items failing DoR should be returned to refinement, not planned |
| Impact/Effort Matrix (2×2) | Phase 4 — prioritization | P1 (high impact, low effort) items are the sprint's non-negotiables; P4 (low impact, high effort) items should be explicitly deferred with a written reason in Jira |
| Focus Factor (capacity model) | Phase 2 individual capacity | Industry benchmark: 0.6–0.7 for most developers; <0.5 signals meeting overload or context switching — investigate before sprint starts |
| SMART Goals (Doran, 1981, *Management Review*) | Phase 7 Sprint Goal review | Applied to Sprint Goals: Specific (names the value delivered), Measurable (has a verifiable done signal), Achievable (fits capacity), Relevant (aligned to product goal/OKR), Time-bound (sprint end = immovable deadline). "Continue features" goals fail Specific — they make sprint success unmeasurable and erode team accountability |

### Key Metrics

- **Team Velocity (rolling 3-sprint avg):** the primary planning input — use 80% of this as the sprint capacity ceiling to build in a safety buffer
- **Individual Utilization %:** (assigned hours / net available hours) × 100 — healthy: 70-85%; >95% = no slack for impediments, almost always results in carry-over
- **Carry-over Probability Score:** based on status at planning time — In Progress >80% = high carry-over likelihood; To Do <45% = genuinely new capacity
- **Bus Factor Coverage:** count of sprint items that only one person can complete — any bus factor = 1 area should have a designated backup or pairing plan before sprint starts
- **Review Load Ratio:** (review hours / productive hours) × 100 — Tech Lead >40% signals too many direct reports to review; creates bottleneck at PR stage

### Expert Decision Criteria

- **If a story has no sprint goal alignment:** don't plan it — ask the Product Owner to articulate which sprint goal this contributes to; "nice to have" is not a sprint goal
- **If carry-over probability >80% for 3+ items from prior sprint:** do not plan new P2 items — resolve the carry-over backlog first; new items will also carry over
- **If utilization exceeds 85% for any member after distribution:** remove one item, not redistribute — adding pressure to an already-full schedule does not reduce carry-over risk
- **If Definition of Ready fails on a story:** flag in Phase 4, do not silently include it — planning an unready story is the single largest source of mid-sprint scope confusion
- **If sprint has no clear, singular sprint goal:** the sprint is a feature factory, not a Scrum sprint — push back and ask the Product Owner to identify the one outcome this sprint advances

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Sprint over-committed every time | Capacity calculated in items/sprint, not hours | Switch to focus-factor-adjusted hours; include review load and carry-over hours before any new assignment |
| Team splits on estimation during planning | No shared Definition of Done; different complexity models | Run one round of planning poker on a reference story before starting; anchor the team's scale |
| Sprint goal too vague ("continue features") | Product Owner hasn't defined value increment | Require SMART goal format; reject "continue" goals — they make sprint success unmeasurable |
| Junior devs consistently under-deliver | Items assigned beyond skill level without pairing | Match skill_profile to task complexity; add pairing note in the Jira issue for any task assigned 1 level above DoR |
| Subtask dates outside parent range (HR8 violations) | Subtask estimates set independently from parent | Always run `sprint_subtask_alignment.py` post-execution; it is the HR8 safety net |

### Authoritative References

- **Scrum Guide 2020 (Sutherland/Schwaber):** Sprint Planning is timeboxed to 8 hours for a one-month sprint. "The Sprint Goal, the Product Backlog items selected for the Sprint, plus the plan for delivering them are together referred to as the Sprint Backlog."
- **Scrum Patterns — Yesterday's Weather (Coplien/Harrison, 2010):** The Yesterday's Weather pattern advocates using recent actual velocity as the primary planning input rather than theoretical capacity; practitioners across the Scrum community consistently report improved sprint predictability when planning to rolling velocity vs. capacity estimates. (Note: the "25-40%" figure circulates widely in Scrum communities but does not appear verbatim in the Coplien/Harrison text — treat as practitioner consensus, not a controlled study result.)
- **Roman Pichler — Definition of Ready:** "Using a DoR helps teams avoid pulling in items that are not sufficiently understood, thereby reducing the risk of incomplete work and carry-over."
