## 🎓 Domain Expert Notes

### Why This Approach

Bug triage separates _severity_ (technical impact on the system) from _priority_ (business decision on when to fix), preventing critical data-loss bugs from sitting in the backlog because a stakeholder did not flag them as urgent. The structured intake-before-scoring sequence ensures the severity decision is always evidence-based, not reactive.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| ITIL Incident Classification | Phase 2 severity matrix (P1/P2/P3) | Aligns bug severity to service-impact tiers used in enterprise incident management |
| ISO/IEC 25010 Quality Characteristics | Phase 2 criteria (security, reliability, usability) | Provides a principled vocabulary for "what makes a bug critical" beyond gut feel |
| DORA Change Failure Rate | Post-sprint defect tracking via P1/P2 labels | P1 bugs contribute to change failure rate; tracking them enables MTTR measurement |
| Defect Life Cycle (IEEE 1044) | Phases 1–5 workflow (intake → assign → create) | Standard defect workflow ensures full traceability from detection to resolution |

### Key Metrics

- **Defect Escape Rate:** % of bugs found in production vs. QA — target < 10%; high escape rate signals weak test coverage in `/create-testplan`
- **MTTR (Mean Time to Resolve):** Time from bug creation to Done status — P1 target < 24h, P2 < 1 sprint, P3 < 3 sprints
- **Duplicate Rate:** % of triage sessions that find a duplicate in Phase 3 — > 20% signals missing test coverage or poor story decomposition
- **Severity Distribution:** Healthy backlog = < 5% P1, < 30% P2, > 65% P3 — inversion signals systemic quality problems

### Expert Decision Criteria

**Severity vs Priority distinction (common confusion):**

- _Severity_ = technical damage (data loss, system down, security breach) — set by QA/engineer in Phase 2
- _Priority_ = business urgency (when to fix) — set by product owner, may override severity
- A P1 severity bug on a deprecated feature may have low business priority — document the divergence explicitly

**P1 escalation triggers (immediate action required):**

- Any bug involving PII exposure or auth bypass → Freeze deployments immediately, escalate to Tech Lead + legal/security team; treat as a security incident, not standard triage
- Payment or financial transaction failure → Freeze deployments if occurring in production, escalate to Tech Lead within 15 minutes; document all affected transaction IDs before investigating
- Database corruption or data loss → Freeze deployments immediately, escalate to Tech Lead, notify all stakeholders; do not attempt manual recovery without senior oversight

**Assignee skill matching (Phase 4):**

- Backend-only bugs → assign to BE developer; avoid assigning to junior without senior pairing for P1
- Cross-service bugs → assign to Tech Lead for root cause analysis first, then delegate fix
- Intermittent bugs → always assign to senior developer; intermittent = complex race condition or infra issue

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| P1 bugs found only in production | QA test plan does not cover critical paths | After fix, use `/create-testplan` with explicit regression cases for the affected path |
| Duplicate bugs split the fix effort | Phase 3 skipped or keywords too narrow in JQL | Always search both semantic (`cache_search`) and keyword (`jira_search`) before creating |
| Severity scores keep getting changed post-triage | Incomplete intake in Phase 1 (frequency, affected users missing) | Gate Phase 1 strictly — all 8 intake fields required before proceeding to scoring |
| P1 bug assigned to junior developer | Phase 4 recommendation logic bypassed by user | Enforce: P1 assignee must have `backend: expert` or `frontend_admin: expert` in skill_profile |
| Bug backlog grows without resolution | No MTTR tracking; severity labels not reviewed in sprint planning | Add P1/P2/P3 label filters to sprint board; review aging P2s in every sprint planning session |

### Authoritative References

- **ITIL 4 (Axelos):** Incident severity levels — the P1/P2/P3 matrix directly maps to ITIL's Critical/High/Medium service impact tiers
- **ISO/IEC 25010:2011 (SQuaRE):** System quality model — security, reliability, and usability characteristics define what constitutes a "critical" bug
- **DORA (Accelerate, Forsgren et al.):** Change failure rate and MTTR are two of the four key DevOps metrics; bug severity labeling feeds these measurements directly
- **IEEE 1044-2009:** Standard classification of software anomalies — provides the formal basis for defect lifecycle phases used in this skill
