# Example

**Input:** "สร้าง story + subtasks สำหรับ admin ดู ad report แบบ monthly"

**Output:**

- Story `ABC-3100`: [FE-Admin] - ดู Ad Report แบบรายเดือน (Monthly Ad Report)
  - AC1: Display — แสดง report table with impression, click, revenue per billboard
  - AC2: Filter — เลือกเดือน/ปี แล้ว report อัปเดตตามช่วงเวลา
  - AC3: Export — กดปุ่ม export ได้ไฟล์ CSV
- Sub-tasks:
  - `ABC-3101` [BE] - API endpoint `GET /api/reports/monthly` with date range filter
  - `ABC-3102` [FE-Admin] - Monthly report page + table component
  - `ABC-3103` [FE-Admin] - CSV export from report data
