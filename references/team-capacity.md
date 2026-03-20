# Team Capacity Reference

## Data Reference

Team roster, avg throughput per member:
→ `.claude/project-config.json` (auto-loaded every session)

Git evidence, bus factor, growth tracks, cross-training, review cost, velocity history:
→ `.claude/project-config-team-detail.json` (load on-demand for sprint planning)

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

## Skill Level Multipliers

> Skill levels determine task assignment fitness

| Level | Multiplier | Usage |
| ----- | ---------- | ----- |
| expert | 1.0x | Can handle complex tasks independently |
| intermediate | 0.8x | Can handle standard tasks, may need review for complex |
| basic | 0.6x | Can handle simple tasks, needs guidance for standard |

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

> **Note:** High raw throughput on small fixes (XS/S) doesn't equal capacity for complex tasks. Use complexity-adjusted throughput for planning.

## Complexity Weighting

> Throughput alone is misleading — 14 small fixes ≠ 6 complex features. Use complexity-adjusted throughput for planning.

```
Complexity Factor: 1.0 = mostly M/L tasks, 0.5 = mostly XS/S tasks, 0.6-0.8 = mixed
Adjusted Throughput = raw avg_throughput × complexity_factor
```

> Per-member raw throughput: see `project-config.json → team.members[].avg_throughput`. Git evidence (dominant task size): see `project-config-team-detail.json → git_evidence`.

## Review Load Formula

> Junior work requires code review → costs reviewer capacity. Factor this into sprint planning.

```
Review Load (per reviewer) = count(reviewees) × review_cost.hours_per_junior_per_sprint
Net Available = Productive Hours - Review Load - Already Assigned
```

> Reviewer map and `hours_per_junior_per_sprint`: see `project-config-team-detail.json → review_cost`.

**Impact on Productive Hours:**

| Reviewer | Base Productive Hrs | Review Load | Net Available |
|----------|-------------------|-------------|---------------|
| Tech Lead | 40h | -15h | **25h** for own work |
| Sr. Backend | 48h | -4h | **44h** for own work |

> Already partially captured in focus_factor (Tech Lead 0.5 includes review time). But when juniors have more items → review load increases proportionally.

## Skill Matrix

> Use `project-config.json → team.members[].skill_profile` for per-person levels. This table shows team-level coverage by area.

| Skill Area | Primary (expert) | Secondary (intermediate) | Basic |
| ---------- | ---------------- | ------------------------ | ----- |
| Backend API | Sr. Backend, Tech Lead | Jr. Full Stack × 2 | Frontend Dev |
| Frontend (Admin) | Tech Lead | Jr. Full Stack × 2 | Frontend Dev |
| Frontend (Web) | Frontend Dev | Jr. Full Stack × 2 | Sr. Backend |
| Mobile (Flutter) | Frontend Dev | — | — |
| Database/Complex | Sr. Backend, Tech Lead | — | Jr. Full Stack |
| DevOps/Infra | Tech Lead | Sr. Backend, Frontend Dev | Jr. Full Stack |

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
