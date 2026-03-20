# create-testplan: Examples

## Example

**Input:** `/create-testplan ABC-2468` (story: admin filter coupon by status)

**Output:**

- `ABC-2471` [QA] - Test: Coupon Status Filter
  - TC1: Filter active — กรอง active แล้วแสดงเฉพาะ active coupons
  - TC2: Filter expired — กรอง expired แล้วแสดงเฉพาะ expired coupons
  - TC3: Clear filter — กด clear แล้วกลับมาแสดงทั้งหมด
  - TC4: Empty state — กรอง status ที่ไม่มี coupon แล้วแสดง empty message
