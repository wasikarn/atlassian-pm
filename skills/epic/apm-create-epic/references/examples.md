# Examples

## Example 1: Vibe Mode (Default)

**Input:** "สร้าง epic สำหรับระบบ coupon management ทั้งหมด"

**Output:**

- Epic `ABC-2800`: [Platform] - ระบบจัดการ Coupon (Coupon Management System)
  - RICE: R=8 I=7 C=0.8 E=3 → Score 14.9
  - Scope: 5 stories (Create, List, Redeem, Report, Settings)
- Epic Doc: Confluence page with overview, business value, VS plan

## Example 2: Thorough Mode with RICE

**Input:** `/create-epic --thorough "Payment Integration"`

**Output:**

```text
Phase 1: Discovery
  → Business Context: Need to accept credit card payments
  → User Impact: Checkout conversion +15% (based on research)

Phase 2: RICE Scoring
  → Reach: 10 (all users)
  → Impact: 3 (massive)
  → Confidence: 0.6 (prototype tested)
  → Effort: 8 (person-months)
  → RICE Score: 2.25

Phase 3: Scope Definition
  → Must-Have: Credit card, saved cards
  → Nice-to-Have: Apple Pay, Google Pay
  → Deferred: Crypto, BNPL

Phase 4: Quality Gate
  → QG Score: 94/100 ✅

Phase 5: Create
  → Epic: ABC-2900
  → Epic Doc: Created
```

## Example 3: From Blueprint Handoff

**Input:** `/create-epic` (after running `/blueprint`)

**Output:**

```text
Phase 1: Discovery
  → Blueprint detected: Using blueprint_backlog_map from previous session
  → Epic Title: Video Upload Progress Indicator
  → Services: [BE], [FE-Web]

Phase 2: Skip RICE (vibe mode)
  → Using RICE from blueprint: R=5 I=2 C=0.7 E=2 → Score 3.5

Phase 3: Scope
  → Tasks: 4 (from blueprint decomposition)
  → Total SP: 13

Phase 4: QG Score: 91/100 ✅

Phase 5: Create
  → Epic: ABC-3000
  → Tasks: ABC-3001, ABC-3002, ABC-3003, ABC-3004
```
