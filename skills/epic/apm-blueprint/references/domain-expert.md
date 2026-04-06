## 🎓 Domain Expert Notes

### Why This Approach

Multi-perspective debate before any Jira artifact is created mirrors Jeff Patton's story mapping principle: shared understanding built through structured conversation is more valuable than any document. The 5-role structure (PO, Domain Expert, TL, Engineer, QA) surfaces assumption mismatches early, when the cost to resolve them is a conversation rather than a sprint of rework.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Jeff Patton — User Story Mapping | Phase 9 Bridge (backlog map) | Backbone = user activities (S2 scenarios); slices = MVP vs. deferred; forces outcome-first decomposition, not feature-list thinking |
| Jobs-to-be-Done (JTBD) | S2 Business Case & User Scenarios | Scenarios written as "when [situation], I want to [motivation], so I can [outcome]" anchor debate in user need, not solution shape |
| Feature Tree / Opportunity Solution Tree | S3 Domain Analysis + S8 Delivery Plan | Distinguishes opportunities → solutions → experiments before committing to implementation |
| Six Thinking Hats (de Bono) | Roles architecture (PO=Yellow/Green, TL=Black/White, QA=Black, Eng=White) | Forcing each role to reason from a single lens prevents groupthink in Round 1; Round 2 cross-challenge is the integration step |
| Lean Startup Build-Measure-Learn | S6 Risks + S8 Delivery Plan → Spikes | Open questions are converted to spike stories (timebox experiments), not assumptions baked into delivery |

### Key Metrics

- **Debate resolution rate:** Number of "disagreements" in the Debate Summary Table that have a Resolution vs. still open — target 100% resolved before writing to Confluence
- **Tier calibration accuracy:** Tier S features should result in 1-2 stories, M in 3-5, L in 6+; post-blueprint count vs. tier prediction validates sizing judgment over time
- **Assumption-to-spike ratio:** For M/L blueprints, S6 open questions should yield at least 1 spike story; 0 spikes on a complex feature is a signal that risks were rationalized away
- **Blueprint-to-epic conversion lag:** Time between blueprint Confluence page creation and `/create-epic` call; >1 sprint is a signal the blueprint lost stakeholder momentum

### Expert Decision Criteria

- **When to force Tier L:** Any feature that introduces a new bounded context (new domain entity that didn't exist before), crosses 3+ services, or has no prior art in the codebase — regardless of story count estimate
- **When S2 must come before S4:** If the TL presents an architecture before the PO has validated the user scenario, the design optimizes for implementation convenience, not user outcome. S1-S2 gate is non-negotiable
- **Alternatives Considered rule:** If only one architecture option is documented, it is not a decision — it is a default. Force at least one "reject and why" even if the team is aligned; documents the reasoning for future maintainers
- **Spike vs. risk:** If a risk has a known mitigation → risk register (S6). If the mitigation itself is unknown → spike story. Conflating the two leaves unknown unknowns in the plan

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| All 5 agents reach identical conclusions in Round 1 | Feature brief is too prescriptive — it pre-solves the design | Rewrite `feature_brief` to describe the *problem*, not the solution; strip implementation hints |
| Round 2 challenges are mild / purely additive | Agents are being polite; no real pressure test | Add explicit adversarial instruction: "Your job is to find the case where the Round 1 proposal fails; be specific and cite evidence" |
| Blueprint exists but `/create-epic` produces generic stories | `blueprint_backlog_map` wasn't passed to the new session | Always chain blueprint → create-epic in the same session; or re-paste the `backlog_map` JSON when resuming |
| S8 delivery plan conflicts with TL architecture in S4 | PO and TL synthesized S8 without re-reading S4 | S8 convergence step must explicitly reference S4 "Alternatives Considered" decision before finalizing sprint mapping |
| QA section (S7) is a generic test type list | QA agent lacked specific ACs to write scenarios against | Feed S2 scenarios to QA Round 1 prompt as explicit input; test scenarios must map 1:1 to user scenarios |

### Authoritative References

- Jeff Patton, *User Story Mapping* (O'Reilly): "The goal of story mapping is shared understanding, not a document" — the 5-role debate IS the mapping; the Confluence page is the record
- Marty Cagan, *Inspired*: Distinguish between output (features shipped) and outcome (user behavior changed); S2 Business Case must state the outcome metric, not just the feature description
- Teresa Torres, *Continuous Discovery Habits*: Opportunity Solution Tree principle — S3 Domain Analysis should map opportunities before jumping to solutions in S4 Architecture
- Bob Marshall / Dan North — Behavior-Driven Design: S7 Test Strategy scenarios in Given/When/Then format are executable specifications, not afterthoughts
