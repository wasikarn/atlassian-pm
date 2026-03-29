## 🎓 Domain Expert Notes

### Why This Approach

Technical debt is a financial analogy (Ward Cunningham, 1992): the "principal" is the effort to fix suboptimal code; the "interest" is the ongoing productivity drag of working around it. The skill's effort × impact priority matrix operationalises this — high-interest debt (high impact, low effort) compounds fastest and must be paid down first, regardless of how old it is.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| Martin Fowler's Tech Debt Quadrant | Phase 3 impact scoring keywords | Fowler's quadrant (Prudent/Reckless × Deliberate/Inadvertent) maps directly to keyword heuristics: "block/security/auth" → Reckless Inadvertent debt (highest interest rate, fix immediately); "refactor/clean" → Prudent Deliberate (acceptable, schedule it); "doc/readme" → Prudent Inadvertent (low interest, low priority) |
| Effort × Impact (Eisenhower-derived) | Phase 3 quadrant assignment | Quick Win (high impact + low effort) / Major Work (high impact + high effort) / Fill-in (low impact + low effort) / Avoid (low impact + high effort) — this is a standard effort-impact triage, commonly applied in tech debt contexts. Note: SQALE uses a separate priority order (quality pyramid); these are complementary, not equivalent |
| SQALE Quality Pyramid (Letouzey, 2012) | Phase 2 age bucketing + Phase 3 keyword priority order | SQALE defines remediation priority as a pyramid: **Testability** (base) → **Reliability** → **Security** → **Maintainability** → **Efficiency** → **Portability** (top). Applied here: `spike` items (testability debt) open > 3 months → structural blockers; `security/auth` keywords → reliability/security layer, always prioritised over `refactor` (maintainability layer); `doc` → bottom-tier unless it blocks testability |

### Key Metrics

- **Tech Debt Ratio:** `(total SP of debt items) / (total SP delivered last 3 sprints)` — industry healthy threshold is ≤20%; above 30% signals velocity ceiling approaching
- **Interest rate proxy:** Count of issues in "Quick Win" quadrant — if Quick Wins accumulate sprint-over-sprint without being picked up, the team is paying interest without reducing principal
- **Debt age distribution:** Percentage of items in "Stale" bucket (>3 months) — target <20% stale; high stale percentage means debt is being logged but never prioritised
- **Resolution rate trend:** Delta computed in Phase 4 (`--update`) — a negative delta (more resolved than added) over 2+ consecutive sprints indicates healthy debt management culture

### Expert Decision Criteria

- If >50% of debt items have no SP estimate → the effort axis of the priority matrix is unreliable; run a quick SP estimation session before using the matrix for sprint planning
- If the "Avoid" quadrant (high effort + low impact) is the largest → these items should be closed as "Won't Fix" or converted to backlog epics; keeping them as active tasks inflates the debt count and hides real priorities
- If `spike` label items are older than 2 sprints → they have become decision debt (a finding not acted on); escalate to the tech lead for a decision to proceed, park, or close
- Scrum teams should allocate 15–20% of sprint capacity to debt reduction (ScrumInc field data; echoed by Google's 20% technical health time — Fitzpatrick & Collins-Sussman, "Team Geek", 2012) — if the `total SP` of Quick Wins exceeds 20% of sprint velocity, the team is under-investing in debt paydown
- If a service tag (e.g., `[BE]`) consistently has the most Stale items → it is a candidate for a dedicated debt-reduction sprint or a mob refactoring session

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Priority matrix is all "Fill-in" (low effort + low impact) | Impact keywords missing from issue summaries | Coach team to write debt issue titles with impact context: "slow" / "blocks" / "recurring" — keyword scoring depends on this |
| `--update` fails with page not found | Tech Debt Radar page was deleted or renamed in Confluence | Drop `--update` flag for one run to recreate, then use `--update` going forward |
| Mermaid quadrant chart renders as raw text in Confluence | Confluence macro renderer not activated for the space | Use `update_page_storage.py` to wrap the Mermaid block in the proper Confluence code macro format (HR4) |
| New debt items appear but trend shows no change | Snapshot HTML comment was manually edited or stripped | Restore snapshot comment format exactly: `<!-- tech-debt-snapshot: {...} -->` with no whitespace changes |
| Debt count grows every sprint with no resolution | Team logs debt but never picks it up | Enforce the 15–20% sprint capacity rule; add a "Debt Review" agenda item to sprint planning |

### Authoritative References

- **Martin Fowler (martinfowler.com/bliki/TechnicalDebt):** "The interest analogy is important — not all debt is bad, but you need to be conscious of both the principal and the interest you're paying"
- **Fowler's Technical Debt Quadrant (2009):** Deliberate+Prudent debt ("we know we're cutting corners now") is the only acceptable form — all other quadrants represent unintentional or negligent debt that should be addressed immediately
- **SQALE Method (Letouzey, 2012):** Remediation priority follows the quality pyramid — fix Testability first, then Reliability, then Security; the keyword-based impact scoring in this skill approximates this order

---
