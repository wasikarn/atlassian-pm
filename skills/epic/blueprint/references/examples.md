## Example

**Input:** "ระบบ notification แบบ real-time สำหรับ platform (push notification + in-app)"

**Phase 2 output:** Tier M — multi-service (BE + Website + Admin), ~4 stories estimated

**Round 1 highlights:**

| Role | Key Points |
|------|-----------|
| PO | 4 scenarios: receive push, view in-app list, mark read, notification preferences. Appetite: 2 sprints. Non-goal: email notifications |
| Domain Expert | 2 bounded contexts: Notification (new) + User Preference (existing). Events: `NotificationSent`, `NotificationRead`, `PreferenceUpdated` |
| Tech Lead | New `NotificationService` Effect service + WebSocket for real-time. Alternative: polling vs WebSocket vs SSE → chose WebSocket. L estimate (5 SP) per story |
| Engineer | Reuse `FCMService` pattern from existing push. 20h total. Gotcha: WebSocket connection management on Next.js |
| QA | "What if user has 1000 unread?" + "notification arrives while user is on notification page?" + "push permission denied?" |

**Round 2 highlights:**

| Debate | Resolution |
|--------|-----------|
| PO wanted notification preferences in MVP | **Kept** — QA flagged edge cases, Engineer confirmed 4h extra is worth it |
| TL chose WebSocket over SSE | **Challenged by Engineer** — SSE simpler for one-way push → **Revised to SSE** for MVP, WebSocket deferred |
| QA's "1000 unread" edge case | **Added pagination** — Engineer confirmed, TL agreed on virtual scroll |
| Domain Expert flagged missing `NotificationBatch` aggregate | **Added** — TL confirmed batch send needed for class reminders |

**Output:** Confluence page with 8 sections + backlog map with 4 stories + 1 spike
