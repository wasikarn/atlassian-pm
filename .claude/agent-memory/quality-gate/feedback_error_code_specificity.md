---
name: AC error codes must be distinct per failure mode
description: Each distinct failure scenario in ACs must reference a unique error code. Reusing a generic error code across ban-block and duplicate-registration scenarios conflates untestable behaviors.
type: feedback
---

Each failure mode in ACs must use a distinct, ban-specific error code — never reuse a generic duplicate/conflict error code.

**Why:** The `phoneAlreadyRegistered` error (or similar) exists for normal duplicate-registration. If a banned-phone re-registration returns the same error, testers cannot distinguish whether the block is due to ban or pre-existing registration. Makes the AC untestable independently.

**How to apply:**

- When writing AC for a "ban blocks re-registration" scenario, verify the error code is ban-specific (e.g. `AUTHUSER003` for email ban, distinct code for phone ban)
- If the codebase doesn't yet have a distinct code, the AC should call for creating one — not reusing an existing generic code
- Cross-check error codes across all ACs in the same story: no two different failure scenarios should share the same error code

Observed in BEP-3432: AC2 (phone ban block) used `phoneAlreadyRegistered` which is also the generic duplicate-phone error — conflation detected during QG.
