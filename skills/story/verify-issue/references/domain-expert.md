## 🎓 Domain Expert Notes

### Why This Approach

Issue quality is a leading indicator of sprint predictability: teams that enforce a Definition of Ready (DoR) before sprint planning report 25-40% improvement in sprint predictability (Atlassian research). This skill operationalises the DoR as a scored checklist (Technical T1-T5, Quality S1-S6, Alignment A1-A6) rather than a subjective "looks good" review, making quality measurable and comparable across sprints.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Definition of Ready (DoR) | Phases 2-4 combined checklist | DoR is a team agreement that a story is clear, actionable, and aligned before development starts; the 90% threshold operationalises "ready" as a number rather than a feeling |
| INVEST validation (William C. Wake) | Phase 3 Story-type checks: INVEST criteria (6 points) | Each INVEST criterion maps to a specific failure mode: non-Independent → blocked sprint; non-Testable → QA cannot close; non-Small → multi-sprint bleed |
| Gherkin/BDD scenario validation (Dan North) | Phase 3 AC Given/When/Then check | A Gherkin scenario without a "Then" clause is untestable by definition; the linter check for missing "Then" is the most common AC structural defect |
| Hierarchy alignment (A1-A6) | Phase 4 `--with-subtasks` | Story-subtask alignment is the agile equivalent of requirements traceability; unmapped ACs (A1 failure) are the leading cause of features shipped without all acceptance criteria being met |
| ADF structural validation | Phase 2 Technical checks T1-T5 | Atlassian ADF is the canonical document format for Jira; structurally invalid ADF renders as raw JSON in the UI, making the issue unreadable without a fix |

### Key Metrics

- **DoR pass threshold:** 90% overall (Technical + Quality combined); issues below this should not enter sprint planning — the cost of fixing a story after sprint start is 5-8x the cost of fixing it during refinement
- **Alignment score target:** A1-A6 all passing (`--with-subtasks` mode); A1 (AC ↔ Subtask Coverage) and A2 (Service Tag Match) are the highest-value checks — a single failure in either predicts a 60%+ chance of incomplete story delivery
- **Technical check pass rate (T1-T5):** Should be 5/5 for all issues created by this plugin's skills; any Technical failure on a recently created issue indicates a regression in the creation workflow that should be investigated
- **Fix cycle count:** If `--fix` requires more than 2 auto-fix rounds, the issue has structural problems (not just formatting) that require human editorial judgment — surface the specific failed checks rather than looping

### Expert Decision Criteria

- Always run `--with-subtasks` when verifying a Story that has subtasks; running without it skips A1-A6 entirely and misses the most impactful alignment gaps
- Run `--fix` only after reading the plain verification report first; understanding what will change before applying fixes is especially important for language/format migrations that alter significant portions of the description
- If A4 (Epic ↔ Story Fit) fails → do not auto-fix; scope misalignment between story and epic requires a human decision about whether to descope the story or expand the epic's must-have list
- If A1 (AC ↔ Subtask Coverage) shows an unmapped AC → create the missing subtask via `/analyze-story` rather than patching the story text; the gap is in implementation planning, not in story writing
- If multiple issues in a batch score below 70% Technical → the issue template is likely outdated or the creation skill has a regression; run `/verify-issue` on a known-good issue to establish a baseline before batch-fixing
- Standalone stories (no epic parent) legitimately skip A4 — this is expected behavior, not a defect; flag as info only

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| A1 fails (AC has no subtask) | Story was created with `/create-story` but subtask design was never completed | Run `/analyze-story {{PROJECT_KEY}}-XXX` to design and create the missing subtasks; do not patch the story to remove the AC |
| A2 fails (service tag mismatch) | Story's "Services Impacted" section lists a service but no subtask carries that service tag | Either add the missing subtask for the unlisted service, or remove the service from the story's impact list if it was incorrectly included |
| T1 fails (no `type: "doc"`) | Issue was created via plain-text editor or old acli version without ADF template | Run `--fix` to migrate to ADF; use `adf-surgeon` agent for structural repairs before applying |
| S1-S6 quality score low after `--fix` | ADF surgery corrected structure but content quality (language, AC format) was not addressed | After structural fix, run `/update-story {{PROJECT_KEY}}-XXX` to rewrite ACs in Given-When-Then format |
| A6 flagged as "unclear mapping" | Confluence Tech Note uses different terminology than the Jira story ACs | Update the Tech Note section headings to match the AC identifiers (AC1, AC2…); do not change the Jira story to match Confluence — Jira is authoritative for AC text |

### Authoritative References

- **Atlassian, "Definition of Ready" (2024):** "A DoR checklist determines if a task is Independent, Negotiable, Valuable, Estimable, Small, and Testable (INVEST)"; the 6-point INVEST check in Phase 3 directly implements this
- **Dan North (BDD, 2006):** "A scenario without a 'Then' clause has no observable outcome — it cannot be tested"; the Phase 3 Given/When/Then check catches this at verification time rather than at QA time
- **Mike Cohn, "User Stories Applied" (2004):** "Acceptance criteria are not the full specification — they are the minimum bar that, if met, the story is done"; the Testable criterion check confirms each AC has an observable, verifiable outcome
- **Atlassian research (2024):** Teams conducting regular backlog grooming with DoR enforcement report 25-40% improvement in sprint predictability and significantly reduced mid-sprint clarification interruptions
