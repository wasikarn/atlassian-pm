## 🎓 Domain Expert Notes

### Why This Approach

Task decomposition quality directly determines sprint predictability: tasks with vague scope or missing acceptance criteria are the #1 cause of sprint carry-over. The four task types (tech-debt, bug, chore, spike) enforce distinct templates because each has fundamentally different done criteria — a spike is done when a decision is made, a chore when a checklist is complete, and tech-debt when the codebase metric improves.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SMART Criteria (Doran, 1981) | Phase 1 required info per type | Ensures tasks are Specific, Measurable, Achievable, Relevant, Time-bound before creation |
| Technical Debt Quadrant (Fowler) | `tech-debt` type classification | Distinguishes reckless/prudent debt — only prudent-deliberate debt belongs in a task |
| Spike Concept (XP/Scrum) | `spike` type template | Spikes have a fixed timebox and a concrete deliverable (ADR, POC, benchmark) — not open-ended research |
| Definition of Done (Scrum Guide) | Quality Gate checks T1–T5 | Each task type has type-specific done criteria baked into the QG checks |

### Key Metrics

- **Task Cycle Time:** Time from "In Progress" to "Done" — target 1–3 days per task; > 5 days signals task is too large (should be split)
- **Carry-over Rate:** % of tasks not completed within the sprint they were planned — target < 15%; high carry-over = poor estimation or scope creep
- **Spike Time-box Compliance:** Spikes should never exceed their stated timebox — a spike that expands is a poorly-scoped spike
- **Tech-debt Ratio:** SP allocated to tech-debt vs. features per sprint — healthy ratio is 15–20% tech-debt to prevent accumulation

### Expert Decision Criteria

**Task sizing thresholds (2-8 hour rule):**

- A task that takes < 2 hours of focused work should be a sub-task, not a standalone Task
- A task estimated > 8 hours should be split into multiple tasks or elevated to a Story with sub-tasks
- Spikes are always timeboxed: state the timebox explicitly in the summary (`[Spike][2d] Evaluate tRPC`)

**Type selection heuristics:**

- Has a PR review comment or linter violation as the origin → `tech-debt`
- Has a clear checklist of mechanical steps with no design decision → `chore`
- Has an unknown outcome and requires investigation before implementation can start → `spike`
- Has observable wrong behavior with repro steps but no severity scoring needed → `bug` (for full triage → `/bug-triage`)

**Traceability requirements:**

- `tech-debt`: must reference the PR number, commit SHA, or review comment that surfaced it
- `spike`: must state the research question AND the expected deliverable (ADR, benchmark, POC) in the summary
- `bug`: must state environment (staging/production) and affected user scope

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Tasks carry over every sprint | Tasks scoped too large (> 8h) or missing ACs | Apply 2-8h rule; ensure every task has testable acceptance criteria before sprint commit |
| Spike never produces a decision | No deliverable defined; open-ended research | Rewrite spike with explicit research question + deliverable type (ADR/POC/benchmark) + timebox |
| Tech-debt backlog grows silently | No PR-to-task traceability; debt recorded informally | Every PR review comment flagged as debt must link to a tech-debt Task within the same sprint |
| Chore tasks re-opened after "Done" | Checklist items were vague or incomplete | Use numbered task list in ADF; each item must be independently verifiable |
| Bug task lacks repro steps | Using `/create-task bug` for complex bugs needing triage | Route to `/bug-triage` for severity scoring, duplicate check, and assignee recommendation |

### Authoritative References

- **Martin Fowler (refactoring.com):** Technical Debt Quadrant — the definitive model for categorizing debt; only "prudent-deliberate" debt should become a planned task
- **Extreme Programming (Beck):** Spike concept — spikes are time-boxed experiments to reduce uncertainty; they always produce a concrete artifact
- **Scrum Guide (Schwaber & Sutherland):** Definition of Done — team-level agreement on what "complete" means; each task type in this skill encodes a type-specific DoD
- **Doran (1981) — Management Review:** SMART objectives — the framework behind the required-info per task type ensures every task is actionable from creation
