# Vertical Slice Guide

> **Reference:** Scrum Guide, StoriesOnBoard, SAFe — applied in BEP project

## Quick Reference

**Vertical Slice = End-to-end user value** across all layers (UI → API → DB)

| Vertical (✅) | Horizontal (❌) |
| --- | --- |
| Full stack for one flow | One layer across flows |
| User can actually use it | Must wait for other layers |
| Independently testable | Must wait for integration |

---

## Pattern Selection Decision Tree

```text
Epic received
    │
    ├─ Is this a new feature area? ─────────────────────→ Walking Skeleton (vs1)
    │                                                     nav + empty states first
    │
    ├─ Are there shared components needed?
    │   └─ Side Panel, Toast, Modal, etc. ──────────────→ Enabler Story (vs-enabler)
    │                                                     build once, use in multiple VS
    │
    ├─ Are there different business rules/types?
    │   └─ Credit vs Discount vs Cashback ──────────────→ Business Rule Split (vs2, vs3, vs4)
    │                                                     one slice per rule
    │
    └─ Does flow span multiple features?
        └─ Coupon → Ad integration ─────────────────────→ Cross-feature
                                                          coordinate with other epics
```

---

## VS Patterns

### 1. Walking Skeleton (vs1-skeleton)

**When:** New feature area, need navigation + empty states first

**Structure:**

- Menu entry + routing
- Empty state UI (placeholder content)
- Basic API shell (optional)

**Example — Coupon System:**

```text
vs1-skeleton
├─ [FE-Web] Menu item "My Coupons"
├─ [FE-Web] Empty state "No coupons yet"
├─ [FE-Admin] Menu item "Manage Coupons"
└─ [BE] GET /v2/coupons/my → empty array
```

**DoD:** User can navigate to feature, sees placeholder, no errors

---

### 2. Business Rule Split (vs2, vs3, vs4...)

**When:** Different business rules/types that can be delivered separately

**Structure:**

- One VS per rule/type
- Each VS delivers complete e2e for that rule

**Example — Coupon Types:**

```text
vs2-credit-e2e (Credit Coupon)
├─ [BE] Credit coupon logic
├─ [FE-Web] Credit coupon UI
└─ [QA] Credit coupon tests

vs3-discount-e2e (Discount Coupon)
├─ [BE] Discount coupon logic
├─ [FE-Web] Discount coupon UI
└─ [QA] Discount coupon tests
```

**DoD:** User can complete full flow for that coupon type

---

### 3. Enabler Story (vs-enabler)

**When:** Shared component needed by multiple VS

**Structure:**

- Reusable component/service
- No direct user value alone
- Enables other VS to deliver faster

**Example — Shared Components:**

```text
vs-enabler-sidepanel
├─ [FE-Web] Side Panel component
├─ [FE-Web] Slide animation
└─ [FE-Web] Close on outside click

vs-enabler-toast
├─ [FE-Web] Toast notification component
├─ [FE-Web] Auto-dismiss logic
└─ [FE-Web] Stack multiple toasts
```

**DoD:** Component works in isolation, documented, other VS can use

---

### 4. Cross-feature (feature-scope)

**When:** Flow spans multiple feature areas or epics

**Structure:**

- Coordinate with related epics
- Clear integration points
- May have external dependencies

**Example — Ad Integration:**

```text
coupon-ad-integration
├─ [BE] Coupon collected → trigger ad event
├─ [BE] Ad service webhook handler
└─ [FE-Web] Show ad after coupon collect
```

**DoD:** Integration works end-to-end, both features updated

---

## VS Decomposition Process

### Step 1: Epic → VS Planning (PM/PO)

```text
1. List all distinct user flows in Epic
2. Identify shared components (→ Enablers)
3. Group flows by business rule (→ Business Rule VS)
4. Decide if skeleton needed (→ Walking Skeleton)
5. Map cross-feature dependencies
6. Assign VS labels
```

**Output:** VS Map table

| VS Label | Pattern | Description | Sprint |
| --- | --- | --- | --- |
| vs1-skeleton | Walking Skeleton | Nav + empty states | N |
| vs-enabler-sidepanel | Enabler | Side Panel component | N |
| vs2-collect-e2e | Business Rule | Collect coupon flow | N |
| vs3-use-e2e | Business Rule | Use coupon flow | N+1 |

### Step 2: VS → Stories (PO)

For each VS:

```text
1. Write user narrative (As a / I want / So that)
2. Define acceptance criteria (Given / When / Then)
3. Add VS label to story
4. Verify story is independently testable
```

**Checklist:**

- [ ] Story delivers value for this VS
- [ ] Story is testable without other VS
- [ ] VS label matches pattern
- [ ] Estimate fits in sprint

### Step 3: Story → Subtasks (TA)

For each Story:

```text
1. Identify affected layers (BE, FE-Web, FE-Admin)
2. Create subtask per layer
3. Each subtask contributes to VS completion
4. Avoid horizontal-only subtasks
```

**Good Example:**

```text
Story: vs2-collect-e2e (Collect Credit Coupon)
├─ [BE] - API and logic for collecting credit coupons
├─ [FE-Web] - UI for collecting credit coupons
└─ [QA] - Test: Collect credit coupons
```

**Bad Example (Horizontal):**

```text
Story: Coupon UI (❌ No VS label, horizontal)
├─ [FE-Web] - Build UI for all coupon pages
├─ [FE-Web] - Build all components
└─ [FE-Web] - Integrate with API
```

---

## VS Definition of Done

### Story Level

| Check | Description |
| --- | --- |
| ✅ **End-to-end value** | User can complete the flow |
| ✅ **All layers touched** | UI → API → DB (or subset if applicable) |
| ✅ **Independently deployable** | Can deploy without other VS |
| ✅ **Testable in isolation** | QA can test without other VS |
| ✅ **VS label present** | `vs{N}-{name}` or `vs-enabler` |

### Anti-pattern Checks

| Anti-pattern | Symptom | Fix |
| --- | --- | --- |
| Shell-only | UI exists but no logic/API | Add minimal happy path |
| Layer-split | BE story + FE story separate | Combine into one VS story |
| Tab-split | "Active tab" / "History tab" as stories | Split by business rule instead |
| Scope creep | VS grows beyond sprint | Re-split into smaller VS |
| Event-split | Domain event lifecycle split across 2 VS | ⚡ One VS handles full command→event flow |
| Consumer-no-emitter | Story consumes event but emitter not in scope | ⚡ Link to producer VS or add dependency |
| Orphaned event | Event emitted but no consumer VS exists | ⚡ Validate downstream VS or defer event |

---

## Horizontal Split Recovery

### Symptoms

- Stories blocked waiting for other stories
- Stories have no direct user value
- Stories touch only one layer
- Testing requires multiple stories complete

### Recovery Process

```text
1. Identify horizontal stories
   └─ [BE] All APIs, [FE] All UIs, [DB] All migrations

2. Group by user flow
   └─ Which APIs + UIs + DB belong to same user action?

3. Rewrite as vertical slices
   └─ "User collects credit coupon" = BE API + FE UI + DB

4. Add VS labels
   └─ vs2-collect-credit-e2e

5. Re-estimate and re-assign
```

### Before/After Example

**Before (Horizontal):**

```text
Sprint 32:
├─ BEP-100: [BE] Build all coupon APIs (5 SP)
├─ BEP-101: [FE] Build all coupon UI (5 SP)
└─ BEP-102: [QA] Test coupon system (3 SP)
    └─ Blocked until BEP-100 + BEP-101 done
```

**After (Vertical):**

```text
Sprint 32:
├─ BEP-200: vs1-skeleton (2 SP)
│   └─ Nav + empty state, deployable Day 1
├─ BEP-201: vs2-collect-credit-e2e (3 SP)
│   └─ BE + FE + QA for collect credit
└─ BEP-202: vs3-collect-discount-e2e (3 SP)
    └─ BE + FE + QA for collect discount

Sprint 33:
├─ BEP-203: vs4-use-credit-e2e (3 SP)
└─ BEP-204: vs5-use-discount-e2e (3 SP)
```

---

## VS Labels Convention

> Full rules: [writing-style.md](writing-style.md) line 171+

| Pattern | When | Example |
| --- | --- | --- |
| `vs{N}-{name}` | Numbered slice | `vs1-skeleton`, `vs2-collect-e2e` |
| `vs-enabler` or `vs-enabler-{name}` | Shared component | `vs-enabler`, `vs-enabler-sidepanel` |
| `{feature}-{scope}` | Cross-cutting | `coupon-ad-integration` |

**Rule:** Every story MUST have:

- Feature label (e.g., `coupon-web`)
- VS label (e.g., `vs2-collect-e2e`)

---

## Sprint Assignment Strategy

| Sprint | Focus | Examples |
| --- | --- | --- |
| Sprint N | Skeleton + Enablers + first E2E | `vs1-skeleton`, `vs-enabler`, `vs2-*` |
| Sprint N+1 | Remaining E2E slices | `vs3-*`, `vs4-*` |
| Sprint N+2 | Polish + cross-feature | Edge cases, `*-integration` |

**Priority within sprint:**

1. Blockers (enablers that other VS need)
2. High-value VS (vs2, vs3)
3. Lower-value VS (vs4, vs5)
4. Polish/edge cases

---

## Related References

- [sprint-frameworks.md](sprint-frameworks.md) — Sprint planning + VS overview
- [writing-style.md](writing-style.md) — VS Labels convention
- [story-best-practices.md](story-best-practices.md) — INVEST + splitting
- [verification-checklist.md](verification-checklist.md) — VS quality checks
