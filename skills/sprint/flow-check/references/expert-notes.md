## 🎓 Domain Expert Notes

### Why This Approach

Flow management is the heart of Scrumban. Unlike Scrum's sprint commitment, Scrumban pulls work based on actual flow — WIP limits, bottlenecks, and replenishment triggers. This skill operationalizes Kanban flow metrics without requiring a dedicated Kanban tool.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| Kanban WIP Limits (David J. Anderson) | Phase 1 board snapshot | WIP limits prevent overloading and expose bottlenecks; the 80% threshold triggers replenishment before queue empties |
| Little's Law | WIP calculation | Average lead time = WIP / throughput; this skill measures WIP, throughput comes from velocity metrics |
| Theory of Constraints (Goldratt) | Bottleneck detection | Columns at ≥80% WIP capacity are constraints; identify and elevate them |
| Scrumban (Ladas) | Replenishment trigger | Ready queue below threshold triggers pull from backlog; this is the "replenishment cadence" automated |

### Key Metrics

- **WIP per Column**: Current count vs WIP limit — shows capacity utilization
- **Flow Efficiency**: (Value-add time / Lead time) × 100 — not measured by this skill but can be inferred from stale issues
- **Replenishment Rate**: How often Ready queue drops below threshold — lower is better (predictable demand)
- **Bottleneck Age**: Issues stuck in a column > 3 days — indicates systemic constraint

### Expert Decision Criteria

- **If Ready queue < threshold**: Trigger replenishment immediately — don't wait for standup
- **If any column ≥ 80% WIP**: Flag as bottleneck — investigate before adding more work
- **If issues > 3 days old in Done**: Blocked — find and remove the blocker (review wait, deployment wait)
- **If Ready queue = 0**: Critical — replenishment is blocked or backlog is empty

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| Ready queue always empty | Backlog not refined | Run `/refine-epic` to groom backlog |
| WIP limits ignored | No enforcement mechanism | Configure board WIP limits in Jira |
| Done column full | Deployment bottleneck | Add deployment automation or dedicated deployment slot |
| Bottleneck shifts to new column | Fixed one constraint, revealed another | Good — continue elevating constraints |
| Replenishment never triggers | Threshold too low or no backlog | Lower threshold or create backlog |

### Authoritative References

- **David J. Anderson, *Kanban* (2010)**: WIP limits, flow metrics, and the Kanban method — the foundational text for Scrumban boards
- **Corey Ladas, *Scrumban* (2009)**: The synthesis of Scrum and Kanban — introduces the replenishment cadence concept used in Phase 2
- **Little's Law**: `L = λW` — the mathematical basis for WIP-based flow management; this skill measures WIP directly
- **Theory of Constraints (Goldratt)**: The Five Focusing Steps — identify, exploit, subordinate, elevate, repeat; this skill identifies constraints in Phase 1
