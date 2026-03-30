# Vertical Slice Guide

> Full rules: [writing-style.md](writing-style.md) · [sprint-frameworks.md](sprint-frameworks.md) · [verification-checklist.md](verification-checklist.md)

## VS Labels Convention

| Pattern | When | Example |
| --- | --- | --- |
| `vs{N}-{name}` | Numbered slice | `vs1-skeleton`, `vs2-collect-e2e` |
| `vs-enabler` / `vs-enabler-{name}` | Shared component | `vs-enabler-sidepanel` |
| `{feature}-{scope}` | Cross-cutting | `coupon-ad-integration` |

**Every story MUST have:** feature label (e.g. `coupon-web`) + VS label (e.g. `vs2-collect-e2e`)

## Pattern Selection

| Signal | Pattern | Label |
| --- | --- | --- |
| New feature area, need nav + empty states first | Walking Skeleton | `vs1-skeleton` |
| Shared component used by multiple VS | Enabler Story | `vs-enabler-{name}` |
| Different business rules/types (credit vs discount) | Business Rule Split | `vs2-…`, `vs3-…` |
| Flow spans multiple feature areas/epics | Cross-feature | `{feature}-{scope}` |

## VS Patterns (Quick Ref)

**vs1-skeleton** — nav entry + empty state + optional API shell. DoD: user can navigate, sees placeholder, no errors.

**vs{N} business rule** — one VS per rule/type, full e2e. DoD: user completes full flow for that type.

**vs-enabler** — reusable component, no direct user value alone. DoD: works in isolation, documented, usable by other VS.

**cross-feature** — coordinate with related epics, clear integration points. DoD: integration works e2e, both features updated.

## Decomposition Checklist

**Epic → VS (PM/PO):**

- [ ] List distinct user flows → assign VS labels
- [ ] Identify shared components → Enabler stories
- [ ] Group flows by business rule → Business Rule VS
- [ ] Decide if skeleton needed
- [ ] Map cross-feature dependencies

**Story (per VS):**

- [ ] Delivers value for this VS
- [ ] Independently testable without other VS
- [ ] VS label matches pattern
- [ ] Estimate fits in sprint

**Subtasks:**

- [ ] One subtask per layer (BE, FE-Web, FE-Admin, QA)
- [ ] Each subtask contributes to VS completion
- [ ] No horizontal-only subtasks (single-layer across all flows)

## Definition of Done

| Check | Criteria |
| --- | --- |
| End-to-end value | User can complete the flow |
| All layers touched | UI → API → DB (or applicable subset) |
| Independently deployable | No dependency on other VS |
| Testable in isolation | QA can test without other VS |
| VS label present | `vs{N}-{name}` or `vs-enabler-{name}` |

## Anti-patterns

| Anti-pattern | Symptom | Fix |
| --- | --- | --- |
| Shell-only | UI exists, no logic/API | Add minimal happy path |
| Layer-split | BE story + FE story separate | Combine into one VS story |
| Tab-split | "Active tab" / "History tab" as stories | Split by business rule instead |
| Scope creep | VS grows beyond sprint | Re-split into smaller VS |
| Event-split | Domain event lifecycle split across 2 VS | One VS handles full command→event flow |
| Consumer-no-emitter | Story consumes event but emitter not in scope | Link to producer VS or add dependency |
| Orphaned event | Event emitted but no consumer VS | Validate downstream VS or defer event |

## Sprint Assignment

| Sprint | Focus |
| --- | --- |
| N | Skeleton + Enablers + first E2E (`vs1-skeleton`, `vs-enabler`, `vs2-*`) |
| N+1 | Remaining E2E slices (`vs3-*`, `vs4-*`) |
| N+2 | Polish + cross-feature (edge cases, `*-integration`) |

**Priority within sprint:** Blockers (enablers) → High-value VS (vs2, vs3) → Lower-value VS → Polish

## Horizontal Split Recovery

Symptoms: stories blocked waiting on others, touch only one layer, no direct user value.

Steps:

1. Identify horizontal stories (`[BE] All APIs`, `[FE] All UIs`)
2. Group by user flow (which APIs + UIs + DB belong to same user action?)
3. Rewrite as vertical slices with VS labels
4. Re-estimate and re-assign
