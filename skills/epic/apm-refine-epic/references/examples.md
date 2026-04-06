## Example

**Input:** "ระบบ waiting list สำหรับ class ที่เต็ม"

**Round 1 highlights:**

| Role | Key Points |
|------|-----------|
| PO | 3 stories: join waitlist, notification, auto-enroll. VS: `vs2-waitlist-e2e` |
| Tech Lead | New `WaitingListEntry` entity + Effect service. Race condition risk. L estimate |
| Engineer | Reuse `BookingService` patterns. Optimistic locking for concurrency. 16h total |
| QA | "2 notified, 1 slot?" + "class cancelled while on waitlist?" + "already booked other class same time?" |

**Round 2 highlights:**

| Debate | Resolution |
|--------|-----------|
| PO wanted auto-enroll in MVP | **Cut** — Tech Lead flagged complexity, Engineer agreed (8h extra) |
| Tech Lead estimated L (5 SP) | **Revised to M+L** — Engineer proposed splitting join (M) vs notify (L) |
| QA's concurrent claim scenario | **Added to AC** — Engineer confirmed optimistic locking handles it |
| QA's "class cancelled" edge case | **Added new AC** — PO agreed it's MVP-critical |

**Output:**

- Story 1: `[FE-Web] - เข้าร่วม waiting list เมื่อ class เต็ม (Join Waiting List)` — M (3 SP)
  - AC1: Display — แสดงปุ่ม "Join Waiting List" เมื่อ class เต็ม
  - AC2: Join — กดเข้าร่วม แล้วแสดง position ใน queue
  - AC3: Concurrent — 2 คนกดพร้อมกัน ได้ position ถูกต้องไม่ซ้ำ
  - AC4: Cancel — ยกเลิก waitlist แล้ว position คนอื่นเลื่อนขึ้น
- Story 2: `[BE] - แจ้งเตือนเมื่อมี slot ว่าง (Waitlist Notification)` — L (5 SP)
  - AC1: Notify — แจ้งคนแรกใน queue เมื่อมีคน cancel booking
  - AC2: Timeout — ถ้าไม่ confirm ภายใน 30 นาที ส่งต่อคนถัดไป
  - AC3: Class Cancelled — แจ้งทุกคนใน waitlist ว่า class ถูกยกเลิก
- **Out of scope:** Auto-enrollment (deferred to vs3)
- **Dependency:** Notification service must be ready before Story 2

→ `/create-story` Story 1 first (no dependency)
