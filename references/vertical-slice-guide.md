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
| Component-split | `[BE] Create FooService` + `[BE] Create BarNotifiable` + `[BE] Hook trigger` as separate stories (all one-layer, each no standalone value) | Combine into VS by business flow; see Case Study below |
| Tab-split | "Active tab" / "History tab" as stories | Split by business rule instead |
| Scope creep | VS grows beyond sprint | Re-split into smaller VS |
| Event-split | Domain event lifecycle split across 2 VS | One VS handles full command→event flow |
| Consumer-no-emitter | Story consumes event but emitter not in scope | Link to producer VS or add dependency |
| Orphaned event | Event emitted but no consumer VS | Validate downstream VS or defer event |

## Case Study — Component-split → Vertical Slice ({{PROJECT_KEY}}-182/183, 2026-04-16)

**Original (wrong):** AI notification Epic broken into 11 technical tasks (lookup service, notifiable class, i18n keys, hook, tests, FE mapping — each single-layer). QA cannot test any task standalone — all just code components. Full 4+ tasks must merge before QA sees working notification.

**Restructured (correct):** 6 vertical slices:

- **Slice A** — single owner TH happy path (1 E2E working feature)
- **Slice B** — multi-owner + EN i18n
- **Slice C** — retry dedup + failure safety

Each slice contains partial work across all layers (lookup + notifiable + i18n + hook + test) but minimal for that specific business outcome. QA tests each slice independently; each slice deployable standalone.

**Lesson:** When tempted to split by code component (`[BE] Create X`, `[BE] Add Y`), check whether the split creates tasks with standalone business value. If no → it's Component-split anti-pattern — merge back into vertical slices by flow.

## Sprint Assignment

| Sprint | Focus |
| --- | --- |
| N | Skeleton + Enablers + first E2E (`vs1-skeleton`, `vs-enabler`, `vs2-*`) |
| N+1 | Remaining E2E slices (`vs3-*`, `vs4-*`) |
| N+2 | Polish + cross-feature (edge cases, `*-integration`) |

**Priority within sprint:** Blockers (enablers) → High-value VS (vs2, vs3) → Lower-value VS → Polish

## Shared Resource Coordination

> **v3.12.1 — G5 (from {{PROJECT_KEY}}-182/{{PROJECT_KEY}}-183 audit):** When 2+ slices touch the same shared component (helper, service, util, shared model), they MUST coordinate to avoid merge conflicts + duplicated commits.

### Coordination Pattern: First-Merged Owns Upgrade

Each slice's AC (or Technical Reference note) MUST include a coordination statement:

> Before implementing `[component]` changes, check if sibling slice `TP-YYY` already merged.
>
> - If merged → `[component]` is already upgraded; this slice only adds tests/coverage.
> - If not merged → this slice implements the upgrade; the sibling slice will later add tests only.

### When to apply

| Signal | Apply? |
| --- | --- |
| 2 slices in same Epic modify the same service | ✅ yes |
| 2 slices across paired Epics modify the same helper | ✅ yes |
| Slice depends on artifact from another slice but doesn't modify it | Add dependency link instead (no coordination needed) |
| Only one slice touches the component | No (coordination adds noise) |

### Example — {{PROJECT_KEY}}-197 ↔ {{PROJECT_KEY}}-200

{{PROJECT_KEY}}-197 (Slice B of {{PROJECT_KEY}}-182) and {{PROJECT_KEY}}-200 (Slice B of {{PROJECT_KEY}}-183) both upgrade `BillboardOwnerLookupService` to `whereIn` pattern. Each ticket includes:

**In {{PROJECT_KEY}}-197 AC list:**

> **Coordination AC:** Before modifying `BillboardOwnerLookupService`, check if {{PROJECT_KEY}}-200 has merged. If {{PROJECT_KEY}}-200 merged → skip lookup-service code change; only add multi-owner integration test. Otherwise → this slice upgrades the service + {{PROJECT_KEY}}-200 adds its test later.

**In {{PROJECT_KEY}}-200 AC list (mirror):**

> **Coordination AC:** Before modifying `BillboardOwnerLookupService`, check if {{PROJECT_KEY}}-197 has merged. If {{PROJECT_KEY}}-197 merged → skip lookup-service code change; only add auto-decision multi-owner test. Otherwise → this slice upgrades the service + {{PROJECT_KEY}}-197 adds its test later.

### Checklist

- [ ] Epic has `Shared Resources` table listing components touched by 2+ slices (see templates-epic.md)
- [ ] Each slice that touches a shared component has a coordination AC
- [ ] Coordination AC references the sibling slice by TP-key (not "the other slice")
- [ ] Mirror: sibling slice has the reverse coordination AC

### Anti-pattern: Silent Shared Upgrade

**Symptom:** Two slices both merge code changes to `FooService.ts`. Second PR fails CI due to merge conflict OR overwrites first PR's logic OR duplicates the same change.

**Root cause:** Neither slice's AC mentions the other; no one realized they were touching the same file.

**Fix:** Declare shared resource in Epic, add coordination ACs to both slices.

## Horizontal Split Recovery

Symptoms: stories blocked waiting on others, touch only one layer, no direct user value.

Steps:

1. Identify horizontal stories (`[BE] All APIs`, `[FE] All UIs`)
2. Group by user flow (which APIs + UIs + DB belong to same user action?)
3. Rewrite as vertical slices with VS labels
4. Re-estimate and re-assign
