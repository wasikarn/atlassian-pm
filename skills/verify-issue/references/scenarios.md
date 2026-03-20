# Scenarios

## Common Scenarios

| Scenario | Command |
| --- | --- |
| Quick check | `/verify-issue ABC-XXX` |
| Check story + subtasks | `/verify-issue ABC-XXX --with-subtasks` |
| Auto-fix single issue | `/verify-issue ABC-XXX --fix` |
| Batch format migration | `/verify-issue ABC-XXX --with-subtasks --fix` |
| Language standardization | `/verify-issue ABC-XXX --fix "standardize Thai"` |

## Integration

| After Command | Verify With |
| --- | --- |
| `/analyze-story` | `/verify-issue ABC-XXX --with-subtasks` |
| `/story-full` | `/verify-issue ABC-XXX --with-subtasks` |
| `/improve-issue` (legacy) | → Use `/verify-issue ABC-XXX --with-subtasks --fix` instead |

## Example

**Input:** `/verify-issue ABC-2468 --with-subtasks`

**Output:**

```text
QG Score: 92/100
✅ ADF structure valid
✅ Panel types correct (info, success)
✅ INVEST: Independent, Valuable, Testable
⚠️ AC2 missing Given/When/Then format (-5)
⚠️ File path `src/pages/coupon.tsx` not found in codebase (-3)
Subtasks: 3/3 aligned with parent ACs
Recommendation: Fix AC2 format, verify file path
```
