## Health Criteria Reference

### Coverage Check

**Objective:** All epic objectives must have at least one corresponding task.

| Condition | Status | Action |
| --- | --- | --- |
| All objectives have tasks | ✅ PASS | None |
| Epic has no objectives | ⚠️ WARN | Add objectives to epic description |
| Objective has no task | ❌ FAIL | Create task or remove objective |

**Blind Spot Detection:** Extract objectives from epic description (bullet points under "Objectives" or "Goals"). For each objective, verify at least one task summary references it.

### Estimation Check

**Objective:** Total story points must be realistic vs team velocity.

| Condition | Status | Action |
| --- | --- | --- |
| Total SP ≤ velocity | ✅ PASS | Fits single sprint |
| velocity < Total SP ≤ 2× velocity | ⚠️ WARN | May need 2 sprints |
| Total SP > 2× velocity | ❌ FAIL | Epic too large, consider splitting |

**Velocity Formula:**

```
velocity = avg(last 3 sprints SP completed)
available = velocity × 0.8 (20% buffer for uncertainty)
```

### Completeness Check

**Objective:** All tasks must have required fields populated.

| Field | Required | Status if Missing |
| --- | --- | --- |
| SP Estimate | Yes | ❌ FAIL: Add estimate |
| Assignee | No (but recommended) | ⚠️ WARN: Assign |
| Sprint | For active sprint work | ⚠️ WARN: Add to sprint |
| Parent (Epic Link) | Yes | ❌ FAIL: Link to epic |

### Timeline Check

**Objective:** Epic must be completable within reasonable timeframe.

| Condition | Status | Action |
| --- | --- | --- |
| Target date not set | ⚠️ WARN | Set target date on epic |
| Estimated completion ≤ target date | ✅ PASS | On track |
| Estimated completion > target date | ❌ FAIL | Reduce scope or extend deadline |

**Estimated Completion Formula:**

```text
estimated_weeks = total_SP / velocity
estimated_completion = start_date + estimated_weeks
```

### AC Alignment Check

**Objective:** All epic acceptance criteria must be covered by task ACs.

| Condition | Status | Action |
| --- | --- | --- |
| Each epic AC maps to ≥1 task | ✅ PASS | Good alignment |
| Epic AC has no task mapping | ❌ FAIL | Create task or remove AC |
| Task AC doesn't map to any epic AC | ⚠️ WARN | May be out of scope |

### Health Score Calculation

```
Health Score = (PASS checks / Total checks) × 100

Status:
- 90-100%: 🟢 Healthy
- 70-89%: 🟡 Needs Attention
- <70%: 🔴 At Risk
```

### Example Output

```text
Epic Health: {{PROJECT_KEY}}-3000 — Video Upload Feature

Coverage: ✅ PASS (4/4 objectives have tasks)
Estimation: ⚠️ WARN (Total 15SP vs velocity 8SP — may need 2 sprints)
Completeness: ❌ FAIL (2 tasks missing SP estimate)
Timeline: ✅ PASS (3 weeks estimate ≤ 4 week target)
AC Alignment: ✅ PASS (All epic ACs covered)

Overall: 🟡 Needs Attention (75%)

Recommendations:
1. Add SP estimate to {{PROJECT_KEY}}-3003, {{PROJECT_KEY}}-3004
2. Confirm epic fits in 2-sprint window or reduce scope
```
