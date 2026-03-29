## 🎓 Domain Expert Notes

### Why This Approach

Release planning at the multi-epic level is a forecasting exercise, not a commitment exercise. The velocity-based timeline (Phase 3) plus dependency-aware sequencing (Phase 4) mirrors SAFe PI Planning's core output — a Program Board showing team commitments and cross-team dependencies across a fixed time horizon.

Three distinct buffer concepts appear in this skill — they are independent, not interchangeable:

- **Velocity buffer (10%):** `effective_velocity = rolling_avg × 0.9` — reserves 10% of sprint capacity for interruptions and unplanned work within each sprint
- **Buffer sprint (10-15% of total release SP):** a dedicated final sprint reserved for stabilisation, testing, and unfinished work — SAFe PI cadence standard
- **Carry-over pre-allocation (20% of buffer sprint):** within the buffer sprint, 20% of its capacity is pre-allocated for carry-over from the prior sprint before any new work is added

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SAFe PI Planning (Program Increment) | Phases 3-5 — sprint sequencing, capacity allocation | PI spans 4-6 sprints with a buffer sprint at the end; the sprint_plan output mirrors a PI plan's epic-to-sprint allocation |
| ROAM Risk Framework (SAFe) | Phase 6 Risk Assessment | ROAM = Resolved / Owned / Accepted / Mitigated; all identified risks must be categorized this way before a release plan is approved |
| Critical Path Method (CPM) | Phase 4 Dependency Analysis | Longest chain of blocking dependencies determines the earliest possible release date regardless of capacity; ignoring critical path produces optimistic but unreachable release dates |
| Agile Release Train (ART) cadence | Phase 3 — effective_velocity calculation | Rolling average SP with 10% buffer matches ART's capacity model for PIs; single-sprint velocity is too volatile for multi-sprint forecasting |
| Definition of Done for releases | Phase 7 Quality Gate | Release DoD: all epics linked, all sprints have dates, critical path documented, risk register populated — these are the release-level exit criteria |

### Key Metrics

- **Release predictability:** Planned SP vs. actual SP delivered at release cut; teams with <15% variance have reliable velocity data; >30% variance signals estimation or scope instability
- **Critical path buffer ratio:** Buffer sprint SP / total release SP; SAFe recommends 1 buffer sprint per PI (typically 10-15% of total capacity); less than 5% leaves no room for unplanned work
- **Dependency density:** Number of cross-epic blocking links / number of epics; >1.5 blocking links per epic signals the release may need to be re-scoped or sequenced differently
- **Risk ROAM completion:** All Phase 6 risks must be ROAM-categorized before Fix Version is created; unROAMed risks are unknown schedule threats

### Expert Decision Criteria

- **When to add a buffer sprint:** Any release with > 3 cross-epic dependencies, any epic with stories not yet pointed, or any external dependency (third-party API, compliance review) not yet confirmed — add a buffer sprint automatically
- **Hard deadline vs. velocity-driven date:** If `--date` is provided and it conflicts with velocity calculation, surface the gap explicitly: "Velocity forecast: [date]. Target: [date]. Gap: [N] SP. Options: (1) reduce scope, (2) increase capacity, (3) move date." Never silently adjust the timeline.
- **Fix Version creation gate:** Fix Version in Jira is a public commitment signal — it appears in release notes, dashboards, and stakeholder reports. Do not create it until the Confluence release plan is reviewed and the scope is stable. Reversing a Fix Version requires manual unlinking of every epic.
- **Carry-over buffer calibration:** If `rolling_avg_sp` from team detail is available, use it. If the rolling average was computed during a sprint with unusual conditions (hackathon, team member out), discount it by 15% for the release plan.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Release date slips every sprint | Velocity used was best-case, not rolling average | Pull the last 6 sprints of actual SP completed; compute trimmed mean (drop highest + lowest); use that as `effective_velocity` |
| Dependencies discovered after Fix Version created | Phase 4 dependency analysis ran on epic-level only, missing story-level blocks | Before creating Fix Version, run a JQL for all `is blocked by` links across all stories in the release, not just epics |
| Buffer sprint fills up immediately | Carry-over stories from previous sprint weren't accounted for | Apply carry-over rule: buffer sprint pre-allocates 20% of capacity for carry-over before any new work is added |
| Scope grows after Fix Version creation ("release scope creep") | No scope freeze process defined | Add a release scope change rule to the Confluence page: any new story added after Fix Version creation requires a corresponding story to be deferred |
| Critical path not visible to stakeholders | Risk register exists but dependency graph is not shown | Include a Mermaid dependency diagram in the Confluence release page (Phase 8) showing critical path highlighted in red |

### Authoritative References

- SAFe 6.0 PI Planning: "PI Objectives are the team's commitment to stakeholders for what will be delivered in the PI; uncommitted objectives are risks, not promises" — Phase 6 risk register maps directly to uncommitted PI objectives
- ROAM framework (SAFe Inspect & Adapt): All risks surface during planning must be ROAMed before the plan is baselined; "we'll handle it" is not ROAM — it must be Owned by a specific person
- Mike Cohn, *Agile Estimating and Planning*: Release planning using velocity requires at least 3 sprints of historical data; fewer than 3 sprints means the estimate is a guess, not a forecast — communicate this to stakeholders
- Atlassian Agile Coach: Fix Versions in Jira are the release coordination mechanism — they drive release notes generation, JQL filtering, and burndown reporting; treat creation as a commitment gate

---
