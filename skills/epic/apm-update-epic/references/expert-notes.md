## 🎓 Domain Expert Notes

### Why This Approach

Epic updates are scope change management decisions, not just text edits. The 6-phase workflow enforces the impact analysis step (Phase 2) that most teams skip, leading to orphaned stories (child stories referencing removed scope) and misaligned burndown charts. The "Preserve Intent" phase (Phase 3) implements the product management principle that core business value should only change with explicit stakeholder re-alignment, not as a side effect of wording improvements.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| SAFe Epic Lifecycle (Portfolio Kanban) | Phase 2 Impact Analysis — change_type classification | SAFe defines four epic lifecycle states: Funnel → Analyzing → Portfolio Backlog → Implementing → Done; scope changes during Implementing require LPM re-approval in SAFe, equivalent to the Phase 2 GATE in this skill |
| Change Impact Analysis (PMBOK) | Phase 2 — impact matrix by change type | Structured impact assessment prevents the "small wording change" that silently invalidates 3 sprint's worth of story ACs |
| Configuration Baseline / Scope Freeze | Phase 3 Preserve Intent rules | Preserving intent mirrors the concept of a configuration baseline — once an epic is in-flight, changes to core business value require a formal change request, not silent editing |
| OKR health check cadence | Monthly epic review model | Epic health reviews (monthly) should ask: (1) Is the OKR this epic supports still valid? (2) Has scope drifted from original hypothesis? (3) Are child stories still aligned to current ACs? |
| ROAM for scope risks | Phase 2 — impact on planning | When scope is removed, blocked stories must be ROAM-categorized: Resolved (story closed), Owned (reassigned to another epic), Accepted (deferred), Mitigated (story scope reduced to fit remaining epic) |

### Key Metrics

- **Epic scope stability ratio:** Number of scope-change updates / total updates on a given epic; > 30% scope changes signals the original discovery phase was insufficient — the epic was created before the problem was understood
- **Child story orphan rate:** After a scope reduction update, percentage of child stories that remain open but reference removed scope; target 0% within 1 sprint of the epic update
- **Update-to-verify lag:** Time between `update-epic` completion and running `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks`; any lag > 24h risks stories and epic ACs diverging silently
- **RICE drift:** Delta between original RICE score at epic creation and current score after updates; > 50% drift means the epic should be re-evaluated for continuation vs. cancellation

### Expert Decision Criteria

- **Scope reduction vs. epic split:** If more than 40% of original scope is being removed, consider creating a new epic for the retained scope rather than editing the current one. Removing scope leaves a confusing history of "what this epic was supposed to be."
- **RICE-only update threshold:** RICE updates that don't change scope (Confidence or Impact revision) are safe to apply without child story review. RICE updates that change Effort imply scope change — treat as scope update and run full Phase 2.
- **Format-only update safety:** Format migrations (ADF panel type changes, section reordering) are genuinely safe only if no AC text is touched. If reformatting requires paraphrasing any AC, it is a scope change, not a format change.
- **When to cascade to child stories:** Scope additions always require new child stories. Scope reductions require closing or descoping existing child stories within the same sprint as the epic update — never leave orphaned stories open.
- **Epic cancellation trigger:** If an update removes > 60% of original scope or the core business value has changed fundamentally, the correct action is to close the epic and create a new one. Heavily edited epics accumulate misleading history that confuses future sprint planning.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Child stories reference scope no longer in epic | Scope was removed from epic but child stories were not updated | Always run `/verify-issue {{PROJECT_KEY}}-XXX --with-subtasks` after any scope change; the A1-A6 alignment checks will surface orphaned stories |
| RICE score becomes stale after market changes | RICE updated at creation, never revisited | Add a monthly epic health review cadence; review RICE Reach and Confidence first — these change most with market/user feedback |
| Epic intent changed silently during "wording cleanup" | Editor paraphrased the business value without noticing the meaning shifted | Phase 3 Preserve Intent check: show Before/After diff of objectives section specifically; any change to the "why" requires stakeholder re-confirmation |
| Multiple small updates create incoherent epic description | Each update optimized its own section without reading the whole | Before generating any update in Phase 4, read the full current epic (Phase 1 fetch) and check narrative consistency end-to-end |
| Fix Version linked to epic with outdated scope | Fix Version was created before scope stabilized | Never create a Fix Version while an epic is actively in scope-change update cycles; wait for scope to stabilize across 2 consecutive sprints |

### Authoritative References

- SAFe 6.0 Lean Portfolio Management: Epics in "Implementing" state require LPM approval for scope changes that affect the MVP definition or Business Outcome Hypothesis — the Phase 2 GATE is the lightweight equivalent for team-level epics
- Atlassian Agile Coach (Jira Epics guide): "As sprints are completed and understanding of customer needs increases, the scope of an epic will change" — planned scope evolution is healthy; untracked scope drift is not
- Roman Pichler — Product Strategy: Epic health reviews should happen monthly and assess both business validity (is the OKR still relevant?) and delivery health (are child stories progressing as expected?)
- Mike Cohn — *Agile Estimating and Planning*: Re-estimation after scope change is mandatory, not optional; teams that update scope without re-estimating carry false velocity data into future sprint planning
