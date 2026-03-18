# Team Capacity Reference

## Capacity Model (Evidence-Based)

> **Source of truth:** `project-config.json` → `team.members[]` + `team.velocity`
> **Sprint Length:** 2 weeks (10 working days)

**Hybrid Model:**

| Level | Metric | Purpose |
|-------|--------|---------|
| **Story** | Story Points (1,2,3,5,8,13) | Team velocity — "how much can we handle this sprint?" |
| **Subtask** | Size (XS/S/M/L) + Estimated Hours | Individual workload — "when will this be done?" |

## Focus Factor (per Level)

Focus Factor = productive dev hours / total available hours

| Level | Focus Factor | Available Hours/Sprint | Productive Hours/Sprint | Reason |
|-------|-------------|----------------------|------------------------|--------|
| Tech Lead | 0.4-0.5 | 80h | 32-40h | Code review, mentoring, architecture, meetings |
| Senior | 0.7-0.8 | 80h | 56-64h | Complex tasks, some review, mentoring |
| Mid | 0.75-0.85 | 80h | 60-68h | Feature work, some review |
| Junior | 0.6-0.7 | 80h | 48-56h | Learning curve, needs code review, pair programming |

## Skill Matrix

> Skill levels determine task assignment fitness (expert=1.0x, intermediate=0.8x, basic=0.6x)

| Skill Area | Primary (expert) | Secondary (intermediate) | Basic |
|-----------|-------------------|--------------------------|-------|
| Backend API | Sr. Backend, Tech Lead | Jr. Full Stack × 2 | Frontend Dev |
| Frontend (Admin) | Tech Lead | Jr. Full Stack × 2 | Frontend Dev |
| Frontend (Web) | Frontend Dev | Jr. Full Stack × 2 | Sr. Backend |
| Mobile (Flutter) | Frontend Dev | — | — |
| Database/Complex | Sr. Backend, Tech Lead | — | Jr. Full Stack |
| DevOps/Infra | Tech Lead | Sr. Backend, Frontend Dev | Jr. Full Stack |

## Throughput Reference (per Person)

> Source: Jira Sprint 28-31 (Nov 2025 - Feb 2026) — tickets completed per sprint

| Slot | Role | Level | Focus Factor | Avg Throughput | Data Source |
|------|------|-------|-------------|---------------|-------------|
| 1 | Tech Lead | Lead | 0.50 | ~6 tickets/sprint | S29-S31 avg |
| 2 | Sr. Backend | Senior | 0.75 | ~6 tickets/sprint | S29-S31 avg |
| 3 | Jr. Full Stack | Junior | 0.65 | ~14 tickets/sprint | S29-S31 avg |
| 4 | Jr. Full Stack | Junior | 0.65 | ~9 tickets/sprint | S29-S31 avg |
| 5 | Frontend Dev + Mobile | Mid | 0.70 | ~4 tickets/sprint | S30-S31 avg (BEP), billboard-owner-app sole dev |
| 6 | QA | — | — | — | — |
| 7 | QA | — | — | — | — |

## Capacity Calculation (Sprint Planning)

### Step 1: Team Velocity (SP-based — when data available)

```
Team Velocity = avg SP completed over last 3-5 sprints
Sprint Capacity = Team Velocity × 0.8 (safety buffer)
```

> **Bootstrap Phase:** Until 3-5 sprints of SP data collected, use throughput-based model below.

### Step 2: Individual Capacity (Hours-based)

```
Available Hours = Sprint Days × 8h × Focus Factor
Productive Hours = Available Hours - (Leave days × 8h × Focus Factor)
Max Subtask Hours = Productive Hours (sum of estimated hours must not exceed this)
```

**Example:**

```
Jr. Full Stack (no leave): 10 days × 8h × 0.65 = 52 productive hours
Sr. Backend (1 day leave): (10-1) × 8h × 0.75 = 54 productive hours
Tech Lead (no leave): 10 × 8h × 0.50 = 40 productive hours
```

### Step 3: Assignment Matching

```
Match Score = Skill Level × (1 + Context Bonus)
  where Context Bonus = 0.2 if assignee has related carry-over items
```

Priority order:

1. Expert with context → assign directly
2. Expert without context → assign
3. Intermediate with context → assign with review
4. Intermediate without context → assign with review
5. Basic → only if no better match, assign with mentoring

## Carry-over Probability (by Jira Status)

| Status | Probability | Rationale |
|--------|------------|-----------|
| To Do | 100% | Not started yet — guaranteed carry-over |
| In Progress | 85% | May finish before sprint end but most carry over |
| TO FIX | 92% | Needs fixing — usually won't finish in one sprint |
| WAITING TO TEST | 55% | Depends on QA capacity; may finish if QA is available |
| TESTING | 45% | Currently being tested; has a chance to finish in sprint |
| Done | 0% | Completed |
| CANCELED | 0% | Canceled |

## Workload Thresholds

> Based on throughput data. Yellow = at historical avg, Red = exceeds historical max.

| Level | Green (OK) | Yellow (At avg) | Red (Over) |
|-------|-----------|----------------|------------|
| Tech Lead | ≤5 items | 6 items | >6 items |
| Senior | ≤5 items | 6 items | >6 items |
| Mid (FE) | ≤3 items | 4 items | >4 items |
| Junior (FS) | varies | at avg_throughput | >avg_throughput |

> **Note:** {{SLOT_3}} has high throughput (~14) due to mostly small fixes (XS/S). Don't use this as benchmark for complex tasks. Adjust threshold by task size mix.

## Complexity Weighting

> Throughput alone is misleading — 14 small fixes ≠ 6 complex features. Use complexity-adjusted throughput for planning.

| Member | Avg Throughput | Dominant Size | Complexity Factor | Adjusted Throughput |
|--------|---------------|---------------|-------------------|---------------------|
| {{SLOT_1}} | ~6 | M/L (complex features, review) | 1.0 | 6 effective |
| {{SLOT_2}} | ~6 | M/L (coupon lifecycle, auth systems) | 1.0 | 6 effective |
| {{SLOT_3}} | ~14 | XS/S (bug fixes, UI tweaks) | 0.5 | 7 effective |
| {{SLOT_4}} | ~9 | XS/S (fixes, wording, locale) | 0.6 | 5.4 effective |
| {{SLOT_5}} | ~4 | M (mobile features, CI/CD setup) | 1.0 | 4 effective |

> **Complexity Factor:** 1.0 = mostly M/L tasks, 0.5 = mostly XS/S tasks, 0.6-0.8 = mixed
> **Adjusted Throughput** = raw throughput × complexity factor — comparable across team members

## Review Dependencies

> Junior work requires code review → costs reviewer capacity. Factor this into sprint planning.

```
{{SLOT_1}} (Tech Lead) reviews:
  ├── {{SLOT_3}} (FE + BE)     ~5h/sprint
  ├── {{SLOT_4}} (FE + BE) ~5h/sprint
  ├── {{SLOT_2}} (BE complex) ~3h/sprint
  └── {{SLOT_5}} (Web + Mobile) ~2h/sprint
  Total review load: ~15h/sprint (of 40h productive = 37.5%)

{{SLOT_2}} (Sr. BE) reviews:
  ├── {{SLOT_3}} (BE only)     ~2h/sprint
  └── {{SLOT_4}} (BE only) ~2h/sprint
  Total review load: ~4h/sprint (of 48h productive = 8.3%)
```

**Impact on Productive Hours:**

| Reviewer | Base Productive Hrs | Review Load | Net Available |
|----------|-------------------|-------------|---------------|
| {{SLOT_1}} | 40h | -15h | **25h** for own work |
| {{SLOT_2}} | 48h | -4h | **44h** for own work |

> Already partially captured in focus_factor (Tech Lead 0.5 includes review time). But when juniors have more items → review load increases proportionally.

## Bus Factor Risk

> Areas with only 1 person who can handle them. If that person is absent, the team is blocked.

| Risk Level | Area | Sole Owner | Backup | Action |
|-----------|------|------------|--------|--------|
| 🔴 Critical | Video Processing | {{SLOT_1}} | None | Document architecture, pair with {{SLOT_2}} |
| 🔴 Critical | DevOps/Infra | {{SLOT_1}} | None | Create runbooks, share access with {{SLOT_2}} |
| 🔴 Critical | Mobile (Flutter) | {{SLOT_5}} | None | Cross-train {{SLOT_3}} on Flutter basics |
| 🟡 Medium | Database/Complex | {{SLOT_1}} + {{SLOT_2}} | None at junior level | Train {{SLOT_3}}/{{SLOT_4}} on migrations |
| 🟡 Medium | Frontend (Web) | {{SLOT_5}} (intermediate) | {{SLOT_3}}, {{SLOT_4}} (intermediate) | No senior expert — Tech Lead is intermediate |

## Growth Tracks (Junior Development)

> Track skill progression to plan gradual responsibility increase.

| Member | Current Strength | Growing Toward | Evidence | Next Step |
|--------|-----------------|----------------|----------|-----------|
| {{SLOT_3}} | FE (Admin+Web) intermediate | BE API intermediate→expert | API commits: Jun=6→Dec=15→Jan=19 | Database basics |
| {{SLOT_4}} | FE (Admin+Web) intermediate | Domain expert (coupon/invoice) | Deep coupon(34)+invoice(16)+accounting(11) | Reduce fix ratio (<40%), API complexity |
| {{SLOT_5}} | Mobile expert | Full-stack mobile+web | Website 9 commits (S31) — starting web | Admin panel basics, more website features |

## Cross-Training Priority

> Reduce bus factor through targeted knowledge sharing.

| Priority | Trainee | Skill | Trainer | Reason |
|----------|---------|-------|---------|--------|
| P1 | {{SLOT_2}} | DevOps basics | {{SLOT_1}} | Bus factor=1, already intermediate |
| P1 | {{SLOT_2}} | Video Processing overview | {{SLOT_1}} | Bus factor=1, backup needed |
| P2 | {{SLOT_3}} | Database (migrations, indexing) | {{SLOT_2}} | Currently basic, growing into BE |
| P2 | {{SLOT_4}} | Database (migrations, indexing) | {{SLOT_2}} | Currently basic, needs BE depth |
| P3 | {{SLOT_3}} | Flutter/Mobile basics | {{SLOT_5}} | Mobile bus factor=1 |
| P3 | {{SLOT_5}} | Backend API basics | {{SLOT_2}} | Currently basic, needed for full-stack |

## Jira Field Integration

> Fields used for machine-queryable capacity tracking (replaces manual ADF extraction)
> **Field IDs:** See `project-config.json → custom_fields` (SSOT for all Jira field IDs)

### Field Mapping

| Concept | Jira Field | Type | Set On |
|---------|-----------|------|--------|
| Story Points | `customfield_10016` | Numeric (1,2,3,5,8,13) | Story, Task |
| Size (T-shirt) | `customfield_10107` | Select (XS/S/M/L/XL) | Story, Task |
| Original Estimate | `timetracking` | Time (`{"originalEstimate":"4h"}`) | Subtask |
| Start Date | `{{START_DATE_FIELD}}` | Date (YYYY-MM-DD) | Story, Task, Subtask |
| Due Date | `duedate` | Date (YYYY-MM-DD) | Story, Task, Subtask |

### Size → Story Points Mapping

| Size | Story Points | Hours (approx) | Subtask Count (typical) |
|------|-------------|----------------|------------------------|
| XS | 1 | < 4h | 1-2 |
| S | 2 | 4-8h | 2-3 |
| M | 3 | 8-16h | 3-5 |
| L | 5 | 16-32h | 5-7 |
| XL | 8 | > 32h | 7+ (must split) |

### Capacity Formula (Field-Based)

```
Sprint Capacity (SP) = sum(story_points) of all planned stories in sprint
  → compare with Team Velocity to detect over-commitment

Individual Load (Hours) = sum(original_estimate) of assigned subtasks
  → compare with Net Available Hours for utilization%

Utilization% = Individual Load / Net Available Hours × 100
  → 🟢 ≤80% | ⚠️ 80-95% | 🔴 >95%

Schedule Check:
  → Subtask start_date ≥ parent start_date (HR8)
  → Subtask due_date ≤ parent due_date (HR8)
  → No overlapping subtask dates for same assignee (warns if >2 concurrent)
```

### Data Source Priority

| Data | Primary Source | Fallback |
|------|---------------|----------|
| Story estimation | `customfield_10016` (Story Points) | Size Guide table above |
| Subtask estimation | `timetracking.originalEstimate` | ADF `⏱️ Estimation` panel |
| Team velocity | `velocity.story_points.avg_velocity` in config | `avg_throughput_per_sprint` (ticket count) |
| Individual workload | JQL: `assignee=X AND sprint=Y` → sum `originalEstimate` | Manual from ADF |
