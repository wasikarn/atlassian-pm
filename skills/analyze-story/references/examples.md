# Example

**Input:** `/analyze-story ABC-2468` (story: admin filter coupon by status)

**Output:**

- `ABC-2469` [BE] - API: เพิ่ม query param `status` ใน `GET /api/coupons` endpoint
- `ABC-2470` [FE-Admin] - UI: สร้าง `StatusFilter` component + integrate กับ coupon list page
- `ABC-2471` [QA] - Test: Coupon Status Filter (4 test cases)
- Technical Note updated on parent story
