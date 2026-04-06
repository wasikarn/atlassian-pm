## 🎓 Domain Expert Notes

### Why This Approach

Pull-based assignment (developers choose work matching their current capacity and skills) consistently outperforms push-based (manager allocates) in throughput and quality — but in mixed-seniority teams, a recommended-then-confirmed model balances autonomy with senior oversight. This skill implements that hybrid: auto-recommend via skill matrix, human confirms.

### Industry Frameworks Used

| Framework | Applied In | Why |
| --- | --- | --- |
| T-shaped skills model (David Guest, 1991; Tim Brown/IDEO, 2010) | Team config `skill_profile` matching | T-shape = deep expertise in one domain (vertical bar) + broad ability to collaborate across others (horizontal bar). `expert` = vertical bar owner; `intermediate`/`basic` = horizontal bar breadth. Assign vertical bar owners to their domain by default; use horizontal bar assignments intentionally for skill growth |
| WIP limits per person (Anderson, *Kanban*, 2010) | Assignment recommendation logic | Anderson: >2 concurrent items introduces context-switching overhead that degrades both throughput and quality. The ≤2 WIP target is the individual-level equivalent of the team-level WIP limit on the Kanban board |
| Skill-based routing (ITIL Service Management) | Phase 4 of bug-triage (service tag → assignee) | ITIL formalises skill-based routing as matching work items to agents with the appropriate skill level — reduces rework by 30-40% in service desk contexts (Axelos, ITIL 4 Foundation) |

### Key Metrics

- **WIP per person:** target ≤ 2 active issues; >3 is a leading indicator of context switching and missed sprint goals
- **Assignment accuracy:** % of issues completed by originally assigned person without reassignment — below 80% signals poor initial matching
- **Time-to-assign:** P1 bugs should be assigned within 15 minutes of creation; P2 within 1 business day

### Expert Decision Criteria

- If `skill_profile[domain] = "expert"` AND current WIP < 2 → strong recommend
- If `skill_profile[domain] = "intermediate"` AND task is P1 → pair with an expert or escalate to Tech Lead
- If `skill_profile[domain] = "intermediate"` AND task is non-critical → this is a **growth assignment** — intentionally assigning 1 level above current skill to develop capability. Growth assignments require: (a) no sprint-critical timeline, (b) senior reviewer listed as watcher, (c) note in the issue description that this is a learning opportunity
- If `focus_factor < 0.6` (e.g., 0.5 for BIG-TATHEP) → reserve for complex/review work, avoid routine chores
- If member has `email: null` → QA roles (kanya, Kanthisorn) cannot be assigned via acli; flag for manual Jira assignment
- Never assign a P1 Critical bug to a single junior without a senior reviewer listed as watcher

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
|---------|-----------|-----------|
| Issue stays unassigned after skill runs | `email: null` in config OR MCP used instead of acli (HR3) | Always use `acli assign`; populate email in config for QA members |
| Same person always overloaded | Assignment ignores current WIP, only matches skill | Check open issues per member before assigning; rotate chores |
| Jira shows wrong assignee | Display name mismatch (Natthakarn case) | Always resolve via `project-config.json` email, never Jira display name |
| Unassigned after "unassign" command | acli called with non-empty string instead of `""` | Use `-a ""` (empty string) not `-a "unassign"` |

### Authoritative References

- **Cognitive Load Theory (Sweller, 1988):** Simultaneous task overload degrades working memory capacity — the empirical basis for WIP limits per person. Sweller's intrinsic, extraneous, and germane load model explains why context switching between 3+ items causes quality degradation beyond what simple multi-tasking studies show
- **Tim Brown, IDEO — "Change by Design" (2009):** T-shaped people are "at the heart of the creative process"; the horizontal bar enables collaboration without requiring cross-domain expertise; use `skill_profile` breadth ratings to find collaborators, not just owners
- **Anderson, David J. — "Kanban" (2010):** WIP limits are the single most impactful change a team can make to improve flow; per-person WIP targets are the individual application of the same principle

---
