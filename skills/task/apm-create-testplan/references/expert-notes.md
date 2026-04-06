## 🎓 Domain Expert Notes

### Why This Approach

Test plans derived directly from Acceptance Criteria (not from implementation) enforce black-box testing — the tester validates what the system _should_ do, not how it does it. The 100% AC coverage mandate prevents the most common QA gap: test cases written for the happy path while edge cases remain untested until production.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| IEEE 829 (Test Documentation Standard) | Phase 3 test case structure (ID, priority, Given/When/Then) | Industry-standard test case format ensures cases are reproducible and auditable |
| ISO/IEC 29119 (Risk-Based Testing) | Phase 2 AC coverage map + priority (🔴/🟠/🟡/🟢) | Priority assignment uses risk exposure (likelihood × impact) to focus test effort on critical paths first |
| ATDD (Acceptance Test-Driven Development) | Phase 2 mapping ACs → test scenarios before Phase 3 | Tests are defined from ACs before implementation detail is known — prevents testing the code instead of the requirement |
| Equivalence Partitioning (Myers) | Edge case (⚠️) and error (❌) test type classification | Input space is partitioned into valid/invalid/boundary classes; one test per class covers the full range |
| Given/When/Then (Gherkin, Cucumber) | Phase 3 test case format | Behavior-driven format makes test cases readable by non-technical stakeholders and linkable to ACs |

### Key Metrics

- **AC Coverage Ratio:** % of ACs with at least one mapped test scenario — must be 100% before Phase 3; < 100% = incomplete test plan
- **Test Case Density:** Number of test cases per AC — typical range is 2–5 cases per AC; < 2 suggests missing edge cases, > 8 suggests over-specification
- **Defect Detection Effectiveness (DDE):** % of bugs found by QA vs. total bugs — target > 90%; low DDE means test plan misses critical scenarios
- **Regression Coverage:** % of previously-failed ACs covered by regression cases — after any bug fix, the fixed AC must gain a regression test case

### Expert Decision Criteria

**Test type selection per AC:**

- AC describes the primary success path → ✅ Happy path test (mandatory for every AC)
- AC mentions limits, counts, or thresholds (e.g., "up to 5 items") → ⚠️ Edge case at boundary value
- AC references an error state or validation rule → ❌ Error/negative test
- AC involves UI interactions or visual feedback → 📱 UI test

**Priority assignment (risk-based):**

- 🔴 Critical: payment flows, authentication, data persistence — test failure = release blocker
- 🟠 High: core feature functionality visible to all users — test failure = release risk
- 🟡 Medium: secondary features, admin-only flows — test failure = known issue, ship with caveat
- 🟢 Low: cosmetic, edge case with workaround — test failure = backlog item

**When to add regression cases:**

- Any AC that was associated with a P1 or P2 bug fix must get a dedicated regression test case
- If a test case was added _after_ a bug was found in production, mark it `[Regression]` in the ID

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Test plan created before ACs are final | Phase 1 gate skipped or ACs still in draft | Enforce Phase 1 gate: check AC status before proceeding; re-run if ACs change |
| Generic TC-01/TC-02 cases with no business context | Phase 2 AC mapping skipped; test cases written from memory | Always complete AC coverage matrix (Phase 2) before writing any test cases |
| Same bug reported in production after QA pass | Edge and error test types missing; only happy path covered | Each AC must have at least one ⚠️ edge or ❌ error case alongside the ✅ happy path |
| Duplicate [QA] sub-tasks for the same story | Phase 1 discovery doesn't check for existing QA subtask | Search for `[QA]` subtask in Phase 1 before creating; if found, update instead of create |
| Test cases fail to catch regressions | No `[Regression]` tagging; P1/P2 fixes not linked back to test plan | After every P1/P2 bug fix, add a regression test case to the story's [QA] subtask |

### Authoritative References

- **IEEE 829-2008 (IEEE Standard for Software Test Documentation):** Defines test plan and test case structure — the ID/priority/Given-When-Then format in Phase 3 follows this standard
- **ISO/IEC 29119-2:2013 (Software Testing Processes):** Risk-based test strategy — the 🔴/🟠/🟡/🟢 priority model maps to ISO 29119's risk exposure classification
- **Glenford J. Myers — "The Art of Software Testing" (1979):** Equivalence partitioning and boundary value analysis — the theoretical basis for edge case (⚠️) test type selection
- **Kent Beck — "Test-Driven Development by Example":** ATDD principle — test cases written from requirements (ACs) before implementation details are known produces better coverage than testing the implementation
