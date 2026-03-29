# VS Checklist (Compact)

> Extract from vertical-slice-guide.md — validation criteria and anti-patterns only.

## VS Definition of Done (Story Level)

| Check | Description |
| --- | --- |
| **End-to-end value** | User can complete the flow |
| **All layers touched** | UI → API → DB (or subset if applicable) |
| **Independently deployable** | Can deploy without other VS |
| **Testable in isolation** | QA can test without other VS |
| **VS label present** | `vs{N}-{name}` or `vs-enabler` |

## Anti-patterns

| Anti-pattern | Symptom | Fix |
| --- | --- | --- |
| Shell-only | UI exists but no logic/API | Add minimal happy path |
| Layer-split | BE story + FE story separate | Combine into one VS story |
| Tab-split | "Active tab" / "History tab" as stories | Split by business rule instead |
| Scope creep | VS grows beyond sprint | Re-split into smaller VS |
| Event-split | Domain event lifecycle split across 2 VS | One VS handles full command→event flow |
| Consumer-no-emitter | Story consumes event but emitter not in scope | Link to producer VS or add dependency |
| Orphaned event | Event emitted but no consumer VS exists | Validate downstream VS or defer event |

## Horizontal Split Symptoms (Recover Immediately)

- Stories blocked waiting for other stories
- Stories touch only one layer
- Testing requires multiple stories complete
- Stories have no direct user value

## Label Rules

Every story MUST have a feature label (e.g., `coupon-web`) AND a VS label (e.g., `vs2-collect-e2e`).

| Pattern | When |
| --- | --- |
| `vs{N}-{name}` | Numbered slice |
| `vs-enabler` or `vs-enabler-{name}` | Shared component |
| `{feature}-{scope}` | Cross-cutting |
