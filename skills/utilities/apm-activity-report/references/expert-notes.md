## 🎓 Domain Expert Notes

### Why This Approach

Activity reports derive from the SPACE framework's "Activity" dimension — tracking developer actions over time to surface patterns, not just outputs. Raw session data (what was done, decided, or discovered) is the rawest signal of engineering work before it gets abstracted into Jira tickets or PR counts.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --------- | --------- | --- |
| SPACE Framework — Activity dimension (Forsgren et al., 2021, *Queue*) | Phase 2–3 output grouping | SPACE Activity = "actions or outputs" (commits, PRs, issues resolved). This skill captures the pre-Jira equivalent: session-level observations before they become tickets. Critically: SPACE explicitly states Activity must be combined with Satisfaction, Performance, Communication, and Efficiency — **activity alone is not a productivity signal** |
| DORA Lead Time proxy | `--hours` range selection | Short-range reports (≤24h) approximate DORA's "lead time for changes" at the individual contributor level; useful for identifying days where work was done but not yet reflected in PRs or Jira |
| OKR progress signal (Doerr, *Measure What Matters*, 2018) | `--types decision,feature` filter | Filtering by decision + feature types extracts the Key Result–relevant signal: what strategic choices were made this week? Absence of `decision` observations for a sprint period → architectural decisions may be undocumented |

### Key Metrics

- **Session depth (variety):** Count of distinct observation types per session — low variety: ≤2 types (all `change` or all `bugfix`) = mechanical/execution work; high variety: ≥4 types (`decision`, `discovery`, `feature`, `bugfix` in same session) = exploratory or design work
- **Decision density:** Ratio of `decision` to total observations per sprint period — target >10% on architecture-heavy weeks; <5% over a full sprint may indicate execution-only mode with undocumented architectural choices; 0% = strong signal to introduce ADR practice
- **Bugfix recurrence:** Same component appearing in `bugfix` observations across 2+ sessions within 5 days = systemic quality debt, not isolated incidents; trigger a root cause review, not just more fixes

### Expert Decision Criteria

- If `--hours 48` returns fewer than 3 observations per day → claude-mem may not be capturing sessions correctly; run `claude-mem status` to verify
- If `--types decision` returns 0 results for a full sprint period → likely missing architectural context documentation; use this as a trigger to add ADR (Architecture Decision Records) practice
- If report is used for team-facing standup → switch to `/standup-report`; activity-report is for individual session archaeology, not team communication

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| ------- | --------- | --------- |
| Output shows 0 observations for a known work day | claude-mem database gap or wrong `--project` filter | Run `claude-mem status` to verify DB health; omit `--project` to see all sessions |
| All observations are type `change` with no `decision` or `discovery` | Sessions ran in non-interactive mode or observations weren't captured | Verify claude-mem hooks are active; check `~/.claude-mem/settings.json` |
| `--start/--end` range returns empty despite known work | Date format mismatch (expects `YYYY-MM-DD`) or timezone offset in DB | Use `--hours N` as fallback; verify system timezone matches DB timestamps |
| Report used by manager to evaluate individual performance | Measurement anti-pattern — activity ≠ productivity | SPACE framework explicitly warns against using activity metrics for performance reviews; use for team retrospectives only |

### Authoritative References

- **Forsgren, Storey, Maddila, Wilson, Zimmermann, Zimmermann — "SPACE: A Framework for Understanding Developer Productivity" (*ACM Queue*, 2021):** "Activity metrics should never be used in isolation — they gain meaning only when correlated with satisfaction and efficiency dimensions." The paper explicitly warns: activity counts are easily gamed (can increase commits/observations without increasing value delivered)
- **DORA State of DevOps Report 2024 (Forsgren, Humble, Kim):** Deployment frequency and lead time are the two DORA metrics most correlated with organizational performance; this skill's `--hours` windowing can serve as a lead-time proxy at the individual level
- **Goodhart's Law (Charles Goodhart, 1975):** "When a measure becomes a target, it ceases to be a good measure." Activity reports expose this risk: if managers reward high observation counts, developers will artificially generate observations. Use for retrospective archaeology only — never as a performance target

---
