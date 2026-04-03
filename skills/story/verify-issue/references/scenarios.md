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
| `/create-story` | `/verify-issue ABC-XXX --with-subtasks` |
| `/improve-issue` (legacy) | → Use `/verify-issue ABC-XXX --with-subtasks --fix` instead |

## Example: Verification Mode

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

## Example: Auto-Fix Mode

**Input:** `/verify-issue ABC-2468 --fix`

**Output:**

```text
Phase 1: Fetch & Identify
  → Issue type: Task
  → Format: ADF (panels detected)

Phase 2: Technical Verification
  ✅ T1: ADF root is doc
  ✅ T2: Panel types valid (info, success)
  ✅ T3: Technical terms inline-coded
  ⚠️ T4: Link to parent exists but parent not found (-2)

Phase 3: Quality Verification
  Score: 88/100
  ✅ Format: ADF panels correct
  ⚠️ Language: Mixed Thai/English - standardizing to Thai
  ✅ Structure: Follows task template
  ⚠️ AC2: Given/When/Then incomplete - fixing

Phase 6: Apply Fix
  → Generated: ~/.claude/artifacts/ABC-2468-fixed.json
  → Applied via: acli jira workitem edit --from-json

QG Score after fix: 94/100 ✅
```
