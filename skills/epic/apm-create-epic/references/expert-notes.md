## 🎓 Domain Expert Notes

### Why This Approach

The 5-phase PM workflow (Discovery → RICE → Scope → QG → Create) encodes the industry-standard separation between problem space (Phases 1-2) and solution space (Phase 3). Committing to scope before validating the problem narrative is the single most common cause of epics that deliver on-time but miss the actual user need. The RICE gate at Phase 2 prevents high-effort low-value epics from entering the backlog through stakeholder enthusiasm alone.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SAFe Epic Hypothesis Statement | Phase 1 Discovery — problem narrative | Every SAFe epic starts as a hypothesis: "We believe [this capability] will result in [this outcome], as evidenced by [this leading indicator]." Narrative Arc is the lightweight equivalent |
| RICE Prioritization (Intercom) | Phase 2 | Converts subjective stakeholder preference into a comparable score; particularly valuable when multiple epics compete for the same sprint capacity |
| Jobs-to-be-Done (Christensen, *Innovator's Dilemma*, 1997; Ulwick, *What Customers Want*, 2005) | Phase 1 — target users + business value | Note: Christensen's JTBD frames the *context* of use ("hire/fire" framing); Ulwick's ODI (Outcome-Driven Innovation) frames *desired outcomes*. Both converge on the same principle for epic work: "When I [situation], I want to [motivation], so I can [outcome]" — prevents solution-first epic definitions |
| OKR → Epic traceability (Doerr, *Measure What Matters*, 2018) | Phase 1 — success metrics | Each epic should trace to at least one Key Result; if it doesn't, question whether the epic belongs in the portfolio at all. OKR-to-epic linkage is the agile equivalent of MBO portfolio alignment — without it, epics optimize for output (features shipped) rather than outcomes (business results) |
| Lean Startup MVP framing | Phase 3 — MVP definition | MVP boundary in VS planning answers: "What is the minimum set of vertical slices that validates our hypothesis?" Not "what is the minimum we can ship" |

### Key Metrics

- **RICE score threshold:** Epics scoring < 5.0 RICE should be challenged or deferred; use as a relative ranking signal, not an absolute gate
- **Discovery-to-scope cycle time:** Time from first stakeholder interview (Phase 1) to approved scope (Phase 3); >2 weeks signals unclear problem ownership or stakeholder availability issues
- **Epic story count at creation:** An epic created with 0 VS stories defined is an idea, not a plan; target 3+ identified stories before QG pass
- **Narrative arc completeness:** All three arc elements present — Current situation, Problem, Solution direction — before Phase 2 starts; missing any one element means the epic scope will drift

### Expert Decision Criteria

- **Epic vs. story threshold:** An initiative that can be delivered in a single sprint by one engineer is a story. An initiative spanning multiple sprints, multiple engineers, or multiple services is an epic. When in doubt, ask: "Can we ship meaningful user value in parts?" If yes → epic.
- **RICE Confidence calibration:** Confidence < 50% signals the team needs a spike or prototype before committing full epic scope. Do not let high Reach × Impact override low Confidence — the denominator (Effort) also has uncertainty at this stage.
- **VS Walking Skeleton rule:** Every epic must include a `vs1-skeleton` story that delivers an end-to-end thin slice users can touch. If the first VS in the plan is purely backend/infrastructure, the PO cannot validate the hypothesis until mid-epic — too late.
- **Blueprint prerequisite gate:** If the epic involves 3+ services or a new bounded context and no `/blueprint` has been run, Phase 1 Discovery will produce a shallow problem narrative. Push back and run blueprint first.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Epic scope grows every sprint ("scope creep") | MVP definition in Phase 3 was aspirational, not minimal | Re-run Phase 3 scope definition with explicit "must-have vs. nice-to-have" binary for each VS story; anything not confirmed must-have defers to next epic |
| RICE score has no effect on sprint planning | Scores calculated but never compared against competing epics | Build a portfolio view: rank all active epics by RICE and review before each sprint planning; enforce WIP limit (config: `team.wip_limit`) |
| Epic created with no Epic Doc | Phase 5 Confluence create was skipped | Epic Doc is not optional — it is the single source of truth for scope decisions; recreate via `/update-epic {{PROJECT_KEY}}-XXX "create epic doc"` |
| Discovery narrative agrees with stakeholder's pre-existing solution | PM accepted solution framing without surfacing the problem | Restart Phase 1 with the "5 Whys" — ask why the proposed solution is needed until a root problem emerges; document that as the narrative |
| Vertical slices are backend-only for first 2 sprints | Team decomposed by technical layer, not user value delivery | Apply the walking skeleton rule: vs1 must be end-to-end (even if thin); reject any VS plan where the first user-visible slice appears past Sprint 2 |

### Authoritative References

- Cprime / SAFe: "No hypothesis, no epic" — the Epic Hypothesis Statement (For / Who / The / Unlike / Our solution) is the quality gate for entering the portfolio Kanban
- Sean McBride, Intercom (RICE framework): Confidence is the most under-valued RICE input; teams routinely inflate it, which is why low-confidence items need spikes, not estimates
- Marty Cagan, *Inspired*: "Fall in love with the problem, not the solution" — Phase 1 Discovery exists to prevent teams from writing epics backward from a pre-decided implementation
- SAFe 6.0 Lean Portfolio Management: Epic MVP must be defined before the epic is approved for implementation; MVP = the minimum investment needed to validate or invalidate the hypothesis
