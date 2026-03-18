# Dependency Frameworks Reference

## Table of Contents

- [Dependency Types](#dependency-types)
- [Three-Step Resolution](#three-step-resolution)
- [Critical Path Method](#critical-path-method)
- [Decoupling Patterns](#decoupling-patterns)
- [Swim Lane Rules](#swim-lane-rules)
- [Risk Scoring](#risk-scoring)

## Dependency Types

### Finish-to-Start (FS) — Most Common

Task B cannot start until Task A finishes.

```text
A ──finish──> B starts
```

**Example:** BE API endpoint must be deployed before FE integration testing.
**Mitigation:** API Contract First + MSW mocks (see Decoupling Patterns).

### Start-to-Start (SS)

Task B starts when Task A starts (parallel with shared prerequisite).

```text
A starts ──> B starts (run in parallel)
```

**Example:** FE and BE both start after API contract is agreed.

### Finish-to-Finish (FF)

Task B cannot finish until Task A finishes.

```text
A ──finish──> B can finish
```

**Example:** QA testing cannot complete until all bug fixes are merged.

### Cross-Team

Different team members' work depends on each other.

```text
Member X (Task A) ──> Member Y (Task B)
```

**Example:** Junior dev's FE page needs Senior dev's API endpoint.

### Inferred Dependencies (not in Jira links)

Some dependencies are implicit — not captured as issue links:

- Same API/module modified by multiple tickets → merge conflict risk
- Shared database migration → must coordinate order
- Shared component/service → interface must be agreed first
- Deploy order constraints → BE before FE for new endpoints

## Three-Step Resolution

### Step 1: Eliminate

Remove the dependency entirely.

| Pattern | How |
| --- | --- |
| MSW Mocks | FE develops against mock handlers, no real BE needed |
| Interface-First | Define TypeScript interface/OpenAPI spec → both sides develop independently |
| Feature Flags | Deploy incomplete features behind flags, no deploy order dependency |
| Duplicate Data | Copy shared data instead of sharing → removes coupling |

### Step 2: Mitigate

Reduce the dependency's impact.

| Pattern | How |
| --- | --- |
| API Contract First | Agree on API shape (types, routes, payloads) in 1-2 hours, then parallelize |
| Staggered Start | Start dependent task 1 day after prerequisite begins (not after it finishes) |
| Partial Delivery | Deliver minimum viable interface early, enhance later |
| Pair Programming | Two developers work on dependent items together |

### Step 3: Accept & Manage

Dependency cannot be removed — schedule carefully.

| Pattern | How |
| --- | --- |
| Critical Path Ordering | Place prerequisite early in sprint, dependent task later |
| Buffer Time | Add 1-day buffer between prerequisite finish and dependent start |
| Daily Standup Flag | Flag blocked items in daily standup for visibility |
| Escalation Path | Define what happens if prerequisite is delayed |

## Critical Path Method

### Algorithm (Agile-adapted)

1. List all sprint items with size estimates (XS=0.5d, S=1.5d, M=2.5d, L=3.5d, XL=5d)
2. Map dependencies between items (Jira links + inferred)
3. Calculate Earliest Start (ES) and Earliest Finish (EF) for each item:
   - ES = max(EF of all predecessors)
   - EF = ES + duration
4. Find the longest path (sum of durations through dependency chain)
5. Items on critical path have ZERO float — any delay = sprint delay

### Float Calculation

- **Total Float** = Latest Start - Earliest Start
- **Zero Float** = Critical path item (must not slip)
- **Positive Float** = Has slack, can be rescheduled

### Agile Adaptations

- Re-evaluate critical path when items complete (rolling lookahead)
- Sprint buffer: reserve 10-20% capacity for unexpected work
- Focus standup on critical path items first
- Merge point buffers: add 0.5d when multiple paths converge

## Decoupling Patterns

### API Contract First + MSW (Mock Service Worker)

The most effective pattern for eliminating FE→BE blocking:

```text
Day 1: Define API contract (OpenAPI spec or TypeScript types)
        ├── BE: Implement real endpoint
        └── FE: Implement with MSW mock handlers
Day N: Swap MSW → real API (zero rework if contract holds)
```

**Contract format:**

```typescript
// Agreed contract — both teams reference this
interface GetCouponsResponse {
  data: Coupon[];
  pagination: { page: number; total: number };
}
// MSW handler (FE team creates this)
http.get('/api/coupons', () => HttpResponse.json({ data: [...], pagination: {...} }))
```

**When to use:** Any FE ticket that needs a BE endpoint not yet built.
**Effort:** ~1-2 hours to define contract + write mock handler.
**Risk:** Contract changes mid-sprint → FE rework (mitigate: freeze contract early).

### Walking Skeleton

Deliver thin end-to-end slice first, then flesh out:

```text
Skeleton: Minimal UI → Minimal API → Minimal DB → Working E2E
Flesh out: Rich UI + Validation + Error handling + Edge cases
```

**When to use:** New features with unknown integration risks.

### Interface-First Development

Define interfaces/types before implementation:

```text
1. Define shared types (30 min)
2. BE implements against types
3. FE implements against types
4. Integration test verifies match
```

## Swim Lane Rules

### Assignment Principles

1. **No idle time**: Every team member should have a task to work on at all times
2. **No blocking waits**: If dependent on someone's output, have alternative work queued
3. **Related items → same person**: Reduces context switching, improves quality
4. **Critical path → senior/lead**: Most experienced developer on highest-risk items
5. **Parallel lanes**: Max items running in parallel = team size

### Scheduling Heuristic

```text
For each team member:
  1. Assign critical path items first (zero float)
  2. Fill gaps with independent items (positive float)
  3. If still blocked → assign spike/tech-debt/refactor work
  4. If still blocked → pair with the person they're waiting on
```

### Buffer Strategy

- Sprint capacity: allocate 80% (leave 20% for unknowns)
- Between dependent items: 0.5-day implicit buffer
- Before sprint review: 1-day integration buffer
- QA testing: starts when first testable item completes (don't wait for all)

## Risk Scoring

### Fan-Out Score

Count how many items depend on a single item:

- **Fan-out ≥ 3**: HIGH risk — single point of failure
- **Fan-out 2**: MEDIUM risk — important but manageable
- **Fan-out 1**: LOW risk — standard dependency

### Delay Impact Score

Estimate cascade delay if item slips by 1 day:

- **Impact ≥ 3 days**: CRITICAL — affects sprint completion
- **Impact 2 days**: HIGH — affects multiple items
- **Impact 1 day**: MEDIUM — affects one downstream item
- **Impact 0 days**: LOW — item has float

### Team Concentration Risk

When >50% of critical path items belong to one person:

- **CRITICAL**: Single person illness = sprint failure
- **Mitigation**: Cross-train, pair program, or split items
