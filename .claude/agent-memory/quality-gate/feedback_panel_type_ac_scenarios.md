---
name: AC panel type selection — rejection/block scenarios
description: Common QG failure pattern: using success panels for AC scenarios that reject/block the user. Block/reject ACs must use error panelType, not success.
type: feedback
---

Block/rejection ACs must use `panelType: "error"`, not `"success"`.

**Why:** `success` panels signal happy-path outcomes. When the AC describes the system rejecting a request (ban block, validation failure, duplicate rejection), using `success` misleads readers and violates the panel semantics defined in templates-core.md.

**How to apply:**

- `panelType: "success"` — use only when the user's intended action completes successfully
- `panelType: "error"` — use when the system rejects, blocks, or throws an error
- `panelType: "warning"` — use for edge cases, regression guards, boundary conditions
- AC naming hint: if the scenario verb is "Block", "Reject", "Deny", "Fail" → the panel should be `error` or `warning`, never `success`

Observed in BEP-3432: AC1 "Block — Banned email rejected" and AC2 "Block — Banned phone rejected" were both marked `success` but are rejection/error-handling scenarios.
