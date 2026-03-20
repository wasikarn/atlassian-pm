# Scenarios

## Common Scenarios

| Scenario | Command | Notes |
| --- | --- | --- |
| Create task from PR review | `/create-task tech-debt "PR #1234 issues"` | Specify type directly |
| Create bug report | `/create-task bug` | Ask for details after |
| Create maintenance task | `/create-task chore "update deps"` | Simple objective |
| Create research task | `/create-task spike "evaluate X"` | Focus on question |

## Example

**Input:** `/create-task tech-debt "refactor coupon service ให้ใช้ repository pattern"`

**Output:**

- Task `ABC-2950`: [BE] - Refactor Coupon Service to Repository Pattern (Tech Debt)
  - Context: coupon service มี direct DB query กระจายใน controller — ยากต่อ testing
  - Scope: `src/modules/coupon/coupon.service.ts`, `coupon.repository.ts` (new)
  - AC1: Extract — ย้าย DB queries จาก service ไป repository
  - AC2: Test — unit test ครอบคลุม repository methods
