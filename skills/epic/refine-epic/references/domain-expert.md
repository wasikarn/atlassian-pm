## 🎓 Domain Expert Notes

### Why This Approach

Backlog refinement fails most often not because requirements are unclear but because they are incomplete from a single perspective. The 4-role debate structure directly addresses this: PO brings user value, TL brings feasibility constraints, Engineer brings implementation reality, and QA brings edge cases that would otherwise surface as bugs in production. Running all four perspectives simultaneously (not sequentially) prevents each role from anchoring on the previous perspective's framing.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SPIDR Splitting (Mike Cohn) | Phase 4 Converge — story splitting decisions | S=Spike, P=Paths, I=Interfaces, D=Data, R=Rules; when a story is too large, SPIDR provides five concrete axes to split on rather than arbitrary chunking |
| Three Amigos (BDD) | Roles structure — PO + Engineer + QA core trio | "Three Amigos" (BA/PO, Dev, QA) is the industry standard for story refinement; the TL is added as a fourth perspective for architectural risk on complex stories |
| INVEST criteria (Bill Wake) | Phase 5 Quality Gate checks | Independent, Negotiable, Valuable, Estimable, Small, Testable — the 6 checks in Phase 5 map directly to INVEST; AC format, SP assignment, VS label, QA coverage, testability, and out-of-scope are INVEST operationalized |
| Behavior-Driven Development (BDD) | AC format: `AC{N}: [Verb] — Given/When/Then` | ACs written in BDD format are executable specifications — QA can write automated tests directly from them without interpretation; "measurable Given/When/Then" is the testability gate |
| Vertical Slice decomposition | VS assignment per story | Each story must deliver end-to-end value (a slice of the cake, not a layer); VS labels enforce this — a story labeled `vs-enabler` must have a follow-on user-facing story that it enables |

### Key Metrics

- **Estimate variance across roles:** Tech Lead SP vs. Engineer SP; variance > 2x signals fundamentally different mental models of scope — surface and resolve, never average
- **AC count per story:** Target 3-7 ACs; < 3 means scope is vague; > 7 means the story should be split (SPIDR: split by Rules or Data)
- **Edge case coverage ratio:** Number of QA edge cases that made it into ACs vs. total QA scenarios proposed; < 50% incorporation rate means QA input is being dismissed without documented rationale
- **Out-of-scope item count:** At least 1 explicit out-of-scope item per story; 0 out-of-scope items means the boundary wasn't interrogated — the story will expand during development

### Expert Decision Criteria

- **When to use SPIDR-Spike vs. proceeding:** If TL and Engineer estimate variance > 3x, the team doesn't understand the implementation — do a Spike (timebox 4-8h) before writing ACs. Writing ACs for an unknown implementation produces fiction.
- **SPIDR-Paths split trigger:** If a user scenario has 3+ distinct happy paths (e.g., upload via API / via UI / via webhook), split into separate stories per path. The first path is vs1-skeleton; remaining paths are vs2+.
- **SPIDR-Rules split trigger:** If a story has business rules that apply to different user segments differently (e.g., free vs. paid users, admin vs. member), split by rule set. Mixed rules in one story = mixed ACs = mixed test scope.
- **QA edge case acceptance rule:** Any QA edge case that is rejected must be explicitly added to the out-of-scope list with rationale. Silently ignoring QA input creates a false sense of completeness in the story.
- **Re-run full debate vs. annotate:** Re-run full Round 2 only if scope changed so substantially that all 4 perspectives need to re-anchor. For AC-level changes, annotate (re-run only the affected roles — PO + QA for AC changes, TL + Engineer for estimate changes).

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Refined stories have 8+ ACs each | Story scope was not split; refinement added detail instead of removing scope | Apply SPIDR-Rules: identify which ACs belong to different business rules or user segments; split into 2-3 stories |
| TL and Engineer estimate differ by 3x | Different assumptions about existing code reuse or new service creation | Resolve in Phase 4 convergence by asking both to state their assumptions explicitly; the disagreement is the finding, not an average |
| QA Round 2 scenarios are identical to Round 1 | QA agent didn't receive the architecture context from TL/Engineer Round 1 | Ensure QA Round 2 prompt includes full TL + Engineer Round 1 output; architectural decisions create new edge cases |
| Stories pass QG but fail in sprint | "Testability" check was formal (has Given/When/Then) but not verified for feasibility | During Phase 5, QA must confirm each AC is automatable with the current test stack (e.g., Cypress for FE, supertest for BE); flag non-automatable ACs explicitly |
| Debate converges too fast (< 2 disagreements) | Agents are anchoring on the feature brief framing | Force at minimum one "what could go wrong" challenge per role in Round 2; if no disagreements, the debate brief was too solution-specific |

### Authoritative References

- Mike Cohn, *Mountain Goat Software* — SPIDR: "The best split is the one that delivers the most learning with the least effort" — always split to maximize early feedback, not to minimize story count
- INVEST criteria (Bill Wake, 2003): Testability is the hardest INVEST property to satisfy and the most commonly violated; if you can't write a test before coding, the AC is not ready
- Dan North — BDD: "The conversation is more important than the documentation" — the debate summary table is the record of the conversation; it has more value than the AC text itself for future maintainers
- Roman Pichler — DEEP backlog: Stories near the top of the backlog must be Detailed appropriately (refined); stories > 2 sprints out should stay coarse — refining them now wastes effort as requirements will change
