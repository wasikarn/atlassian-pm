## 🎓 Domain Expert Notes

### Why This Approach

Sprint closure is a hard boundary event in Scrum — the Scrum Guide (2020) defines the Sprint Retrospective as the final event that concludes the Sprint. Executing closure as a distinct, irreversible operation (rather than a soft archive) enforces accountability: carry-over rate and velocity are recorded at a fixed point in time, enabling honest trend analysis.

### Industry Frameworks Used

| Framework | Applied In | Why |
|-----------|-----------|-----|
| Scrum Guide 2020 Sprint Retrospective | Phase 2 Triage + Phase 7 Metrics | Inspects "what went well, what problems, how solved" — maps directly to Done/Incomplete/Blocked categories |
| Yesterday's Weather (Scrum pattern) | Phase 7 velocity-tracker | Team velocity is the running average of recent sprints (±20% precision); single-sprint data is noise |
| DORA Metrics (Google DevOps Research) | Phase 6 Review Page — Anomalies section | Deployment frequency and change lead time surface in blocked/late-start anomalies; carry-over rate is a proxy for delivery predictability |
| Start/Stop/Continue (Roger Schwarz, adapted by Scrum community) | Post-closure: feeds `/retrospective-analyst` | Simplest actionable retro format — each action maps to a backlog item or team agreement. Schwarz's "Team Effectiveness Model" is the origin; the 3-column format was widely adopted by agile coaches circa 2005-2010 for its low facilitation overhead |
| 4Ls (Liked/Learned/Lacked/Longed For) (Diana Larsen, popularised via Agile Retrospectives) | Optional retro input after page is generated | Richer emotional signal than Start/Stop/Continue; the "Longed For" dimension surfaces aspirational team improvements that "Lacked" alone misses. Most useful when velocity metrics are stable but morale or collaboration quality is declining |

### Key Metrics

- **Sprint Velocity:** SP completed / sprint — target: consistent ±15% of rolling 3-sprint average; spikes >30% indicate scope inflation or counting errors
- **Carry-over Rate:** incomplete / total issues × 100% — healthy: <15%; >30% signals systemic planning overcommitment or blocking dependencies
- **Completion Ratio:** done SP / planned SP — the primary predictability signal; teams with >80% completion consistently outperform on delivery dates
- **Blocked Issue Age:** days an issue has been in Blocked status — >2 days with no resolution attempt = Scrum Master action required
- **DORA Deployment Frequency:** how often code ships per sprint — correlates with carry-over rate; teams that ship daily have <10% carry-over

### Expert Decision Criteria

- **If carry-over rate > 30% for 2+ consecutive sprints:** trigger a planning review — root cause is almost always over-commitment, not execution failure
- **If a blocked issue is moving to the next sprint:** it MUST have a concrete unblocking owner before the move, not just a destination sprint
- **If completed SP < 50% of planned SP:** do not close without a stakeholder notification — this is a delivery risk event, not a routine closure
- **If velocity drops >25% from prior sprint:** flag as anomaly in the Confluence review page before the retrospective, not after
- **Carry-over to next sprint vs. backlog:** In-Progress items default to next sprint only if they have >50% work complete (estimated); otherwise backlog is more honest

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Carry-over rate consistently >30% | Sprint overcommitment; velocity-based capacity not applied | Apply Yesterday's Weather: cap commitment at 80% of 3-sprint avg velocity |
| Velocity appears high but carry-over is also high | SP claimed on partial work; Definition of Done not enforced | Only count SP on issues with status = Done at close time; partial credit is a metric corruption |
| Retrospective insights never actioned | Actions not converted to Jira items with owners | Every retro action item → Jira task in next sprint backlog, assigned at closure |
| Sprint closed with P1 bugs still open | Urgency pressure; no gate before close | HR: enforce pre-close check for open P1/P2 issues; closure is irreversible |
| Confluence review page never read | Page created but not linked or announced | Post link in team channel at closure; add it to the next sprint's Definition of Done checklist |

### Authoritative References

- **Scrum Guide 2020 (Sutherland/Schwaber):** "The Sprint Retrospective concludes the Sprint. It is timeboxed to a maximum of three hours for a one-month Sprint." — closure order matters: retro before close is the correct sequence
- **Accelerate (Forsgren, Humble, Kim):** The four DORA metrics — deployment frequency, lead time, change fail rate, recovery time — are the only engineering metrics proven to correlate with organizational performance; carry-over rate is a leading indicator of degraded deployment frequency
- **Scrum Patterns (Coplien/Harrison):** Yesterday's Weather — "use the team's recent velocity as the primary forecast signal; adjust only for known capacity changes (leave, team size)"
