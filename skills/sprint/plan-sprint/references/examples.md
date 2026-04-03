# Examples

## Example 1: Basic Sprint Planning

**Input:** `/plan-sprint`

**Output:**

```
Sprint 42 (Apr 7-18) | Capacity: 35 tickets
Carry-over: 3 tickets (ABC-XXX, ABC-YYY, ABC-ZZZ)
New work: 32 tickets from backlog
Assignments:
  {{SLOT_1}}: 6 tickets (review + complex BE)
  {{SLOT_2}}: 8 tickets (BE focus)
  {{SLOT_3}}: 10 tickets (FE-Web + FE-Admin)
  {{SLOT_4}}: 7 tickets (FE-Admin)
  {{SLOT_5}}: 4 tickets (Mobile + FE-Web)
Risk: ABC-XXX blocks 2 downstream tickets
```

## Example 2: Carry-Over Heavy Sprint

**Input:** `/plan-sprint` (with 80% carry-over)

**Output:**

```
Sprint 43 (Apr 21-May 2) | Capacity: 40 SP
Carry-over: 32 SP (80% capacity) ⚠️ HIGH
  → {{PROJECT_KEY}}-2845: Payment Integration (85% done, blocked)
  → {{PROJECT_KEY}}-2867: Video Upload (70% done, needs testing)
  → {{PROJECT_KEY}}-2890: Coupon UI (60% done, waiting for BE)

Warning: Carry-over exceeds 80% capacity threshold
Recommendation: Cancel or defer new work; focus on completing carry-over

New work: 8 SP available
Assignments: Prioritize carry-over completion
  → {{PROJECT_KEY}}-2845: Assign to senior (unblock dependencies)
  → {{PROJECT_KEY}}-2867: Pair testing (BE + FE)
  → {{PROJECT_KEY}}-2890: Wait for {{PROJECT_KEY}}-2845 completion
```

## Example 3: Thai Language

**Input:** `/plan-sprint` (Thai team)

**Output:**

```
Sprint 44 (May 5-16) | Capacity: 45 SP
Carry-over: 12 SP (27% capacity) ✅ ต่ำ

งานใหม่: 33 SP
Assignments:
  สมชาย: 8 SP (BE focus + code review)
  สมหญิง: 10 SP (FE-Web + FE-Admin)
  วิภา: 12 SP (FE-Admin lead)
  ธนพล: 8 SP (Mobile + integration)

Risk: {{PROJECT_KEY}}-2900 มี dependency กับ {{PROJECT_KEY}}-2895
Recommendation: ให้ทำ {{PROJECT_KEY}}-2895 ก่อน
```
