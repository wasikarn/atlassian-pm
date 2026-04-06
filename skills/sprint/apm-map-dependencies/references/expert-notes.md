## 🎓 Domain Expert Notes

### Why This Approach

Dependencies are the primary source of value destruction in Scrum — a single blocking dependency can cascade across multiple team members and sprint goals. This skill applies Critical Path Method (CPM) from classical project management to the sprint timebox: every day of float consumed by an unresolved dependency directly reduces the probability of sprint goal achievement.

### Industry Frameworks Used

| Framework | Applied In | Why |
|-----------|-----------|-----|
| Critical Path Method (CPM) | Phase 3 — ES/EF/LS/LF calculation | Identifies which items have zero float (any delay = sprint goal at risk); developed at DuPont/Remington Rand (1957), still the canonical scheduling algorithm |
| Dependency Structure Matrix (DSM) | Phase 2 — dependency graph construction | DSM (Don Steward, MIT, 1981) represents N×N relationships in a square matrix; reveals circular dependencies and parallel execution opportunities that linear lists miss |
| Conway's Law | Phase 2 — Source B inferred dependencies | "Organizations design systems that mirror their communication structure" — if BE and FE are separate teams, every FE→BE dependency is a Conway coupling that should be explicitly mapped and addressed via API contracts |
| Team Topologies (Skelton/Pais) | Phase 4 — mitigation recommendations | Stream-aligned teams minimize dependencies; platform teams absorb them. When fan-out from one team's items is >3, suggest a platform extraction or API Contract First pattern |
| API Contract First / MSW mocking | Phase 4 — decoupling strategy | Eliminates FE→BE blocking dependency within the sprint by agreeing on interface before implementation; standard in modern frontend development |

### Key Metrics

- **Critical Path Duration:** total calendar days on zero-float chain — if >80% of sprint length, the sprint has no buffer for any delay
- **Fan-out Score:** number of items blocked by a single issue — fan-out >3 = single point of failure; assign to your most reliable team member and protect their capacity
- **Dependency Density:** total edges / total nodes in the graph — healthy: <0.5; >1.0 means more dependencies than items, indicating a sprint that should be replanned
- **Team Concentration Risk:** % of critical path items assigned to one person — >60% concentration is a delivery risk; redistribute or pair
- **Inferred Dependency Accuracy:** % of MEDIUM/LOW inferred deps later confirmed — track over time; improve heuristics when accuracy drops below 50%

### Expert Decision Criteria

- **If critical path buffer < 1 day:** treat as HIGH risk immediately — remove the lowest-priority item from the sprint, not from the critical path
- **If circular dependency detected (A→B→A):** this is a design flaw, not a scheduling problem — escalate to architecture discussion before sprint starts; never schedule circular deps within a single sprint
- **If FE→BE dependency exists and BE has >3 other items:** apply API Contract First pattern — define the OpenAPI/TypeScript interface on Day 1, unblock FE with MSW mock
- **If >40% of items are on the critical path:** the sprint is too tightly coupled; split into two smaller parallel tracks or defer items until dependencies resolve
- **If a dependency is MEDIUM/LOW confidence:** always annotate in the Jira comment rather than creating a formal Jira issue link — premature formalization creates noise

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Swim lane shows everyone starts Day 1 but items complete on Day 8-9 | Critical path not identified; all items treated as independent | Run CPM first; schedule critical path items with explicit early-start constraints |
| Dependencies found mid-sprint cause replanning | Inferred dependencies not surfaced at planning | Run `/map-dependencies` before sprint planning, not after; treat Phase 2 Source B as mandatory |
| One team member becomes the sprint bottleneck | High fan-out score on their items undetected | Fan-out >3 = reassign one of their dependencies or add a second owner |
| API dependencies cause FE to idle | No decoupling strategy defined | API Contract First + MSW mock should be in the mitigation output for every FE→BE edge |
| Dependency graph too noisy for 30+ item sprints | No filtering applied | Always use `--keys` to scope to the 8-12 highest-priority items; full-sprint graphs are useful only for program-level planning |

### Authoritative References

- **Conway's Law (Melvin Conway, 1968):** "Any organization that designs a system will produce a design whose structure is a copy of the organization's communication structure." — map organizational boundaries first; dependencies that cross team lines are the highest-risk dependencies
- **Critical Path Method (Morgan/Kelly, 1959):** Zero-float items are non-negotiable — they cannot be delayed without delaying the project end date. In sprint context: zero-float = sprint goal risk
- **Team Topologies (Skelton/Pais, 2019):** "Minimizing cognitive load and dependency surface area between teams is the primary architectural goal" — every cross-team dependency in the graph is an architectural smell worth discussing at the sprint level
