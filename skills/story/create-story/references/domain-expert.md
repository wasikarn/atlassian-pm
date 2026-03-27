## 🎓 Domain Expert Notes

### Why This Approach

User stories are not requirements documents — they are promises of a conversation (Ron Jeffries' 3 Cs: Card, Conversation, Confirmation). This skill forces the PO + TA roles to stay combined through the full workflow precisely because splitting story writing from technical design produces stories that pass INVEST on paper but fail in sprint due to hidden dependencies or infeasible ACs.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| INVEST (William C. Wake, popularised by Mike Cohn) | Phase 3 INVEST + VS Validation | Six-attribute quality gate that distinguishes story-ready items from wish-list items; Small + Vertical are the most commonly violated |
| 3 Cs — Card, Conversation, Confirmation (Ron Jeffries) | Phase 2 Write Story → ITERATE gate | Narrative = Card; annotation cycle = Conversation; AC sign-off = Confirmation; skipping Conversation produces unvalidated assumptions |
| Gherkin / BDD Given-When-Then (Dan North) | Phase 2 AC format `AC{N}: [Verb] — [Scenario]` | Scenario-naming forces testability; unnamed ACs (e.g. "AC1: Login") lack the verb-object structure needed to derive test cases |
| Vertical Slicing (Jeff Patton, "User Story Mapping") | Phase 3 VS Anti-pattern Check | A story that touches only one layer (shell-only, BE-only) is not independently shippable; the map backbone → release slices pattern informs VS label assignment |
| Estimation Calibration (historical throughput) | Phase 9 Estimation Calibration agent | Anchoring estimates to team velocity data (not abstract complexity) reduces estimation variance by 25-40% vs. pure Planning Poker |
| Blueprint-first for complex features | Phase 0 Blueprint Handoff Check | Jeff Patton's "story mapping before story writing" principle — mapping the whole before writing individual stories prevents VS label conflicts and scope gaps |

### Key Metrics

- **INVEST pass rate target:** All 6 criteria must pass before Phase 4; partial passes (4/6, 5/6) are the leading cause of mid-sprint scope creep
- **Story size:** Completable within 1 sprint at ≤ L (5 SP); stories estimated XL (8 SP) should trigger a split discussion before proceeding to Phase 4
- **AC count sweet spot:** 3-7 ACs per story; fewer than 3 indicates insufficient coverage; more than 8 indicates the story spans multiple vertical slices and should be split
- **Discovery round limit:** 3 ITERATE annotation rounds maximum; if consensus isn't reached after 3 rounds, escalate to `/blueprint` to re-scope the feature
- **QG threshold:** 90% before any Jira write; stories created below this threshold have a 3x higher rate of mid-sprint rework based on Atlassian internal data

### Expert Decision Criteria

- If the "Who" in Discovery is vague (e.g. "admin user") → press for the specific persona workflow context; generic personas produce generic ACs that fail the Testable criterion
- If VS assignment is unclear after Discovery → lean toward the lowest numbered VS slice that the story can meaningfully contribute to; it is easier to promote a story up the VS hierarchy than to demote it
- If any INVEST criterion fails after 2 auto-fix attempts → do NOT create the story; surface to the user with the specific failure reason and suggest either splitting or returning to Discovery
- If Story narrative already exists in Jira (user passed a key instead of a description) → stop immediately and redirect to `/analyze-story`; creating a duplicate story is a harder problem to fix than a missing one
- "Shell-only" anti-pattern check: if Phase 5 Impact Analysis shows only FE-Admin or FE-Web impacted with no BE — confirm with the user whether this is truly a pure-UI story or whether AC coverage is incomplete

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Story created without parent epic | `--epic` not provided and no blueprint context | Immediately run `jira_set_parent.py --issues KEY --parent EPIC`; orphan stories corrupt sprint velocity reports |
| ACs written as implementation tasks ("Implement Redis cache") | TA thinking leaked into PO phase | Rewrite ACs as observable user/system outcomes: "System responds within 200ms after cache warms" |
| VS label mismatch across child subtasks | VS label set at story creation without Impact Analysis | Re-run Phase 5 after story is created; update VS label if impact table reveals a different slice |
| Estimation calibrator returns LOW confidence | Team has fewer than 5 historical subtasks of the same service+size combination | Keep initial estimate; note the gap; add a calibration observation after the sprint closes |
| Story fails QG after 2 auto-fix rounds | Narrative and ACs are internally inconsistent (persona in narrative ≠ persona in ACs) | Return to Phase 2 ITERATE; fix narrative-AC coherence before re-running QG |

### Authoritative References

- **Mike Cohn, "User Stories Applied" (2004):** "A story is a placeholder for a conversation, not a specification" — the ITERATE annotation cycle is the operationalised version of this principle
- **Ron Jeffries (XP):** 3 Cs — Card (brief), Conversation (collaborative refinement), Confirmation (acceptance tests); all three must be present for a story to be "ready"
- **Jeff Patton, "User Story Mapping" (2014):** Map the whole user journey before writing individual stories; stories written without a map tend to duplicate or gap the backbone
- **Dan North (BDD, 2006):** Given-When-Then format forces scenario specificity that naked bullet-point ACs cannot achieve; each scenario title should read like a test case name
