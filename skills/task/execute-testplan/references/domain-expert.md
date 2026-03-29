## 🎓 Domain Expert Notes

### ISTQB — Test Execution Lifecycle

Test execution follows a defined cycle: **Entry criteria check → Execute → Log defects → Exit criteria check → Report**. Entry criteria must be verified before Phase 4 (environment up, test data ready, ACs frozen). Exit criteria define when to stop: typically pass rate ≥ 95% for non-critical features, 100% for payment/auth flows. Never execute against an environment that hasn't passed entry criteria — partial results are worse than no results.

### Entry / Exit Criteria

**Entry criteria (Phase 3 pre-flight):**

- Environment reachable and stable (no active deployment)
- Test account credentials available
- Feature branch merged to staging
- All blocking bugs from previous run resolved

**Exit criteria (Phase 6 summary):**

- All test cases executed (pass/fail/skip/blocked)
- All failures have a Jira bug ticket
- Pass rate acceptable for release (define per feature: critical = 100%, standard = ≥ 95%)
- Sheet updated with results and date

### IEEE 829 — Test Execution Record

Each test execution must record: test case ID, execution date/time, environment, tester identity, pass/fail verdict, actual results, and incident references. The Google Sheet columns I–L map directly to this standard. Column L (Remark) serves as the incident reference field.

### Test Type Risk Profile

| Test Type Failure | Severity | Default Priority | Release Impact |
| --- | --- | --- | --- |
| Positive test fails | Critical | High | Block release |
| Negative test fails | Major | Medium | Risk release |
| Edge test fails | Minor | Medium | Ship with caveat |

### Re-testing vs Regression Testing

- **Re-test**: Execute a specific test case that previously failed, after the bug is fixed. Target: the exact failed case only.
- **Regression**: Execute a broader set of test cases to ensure the fix did not break adjacent functionality. Use `--rerun-failed` for re-test; manually expand scope for regression.
- After any bug fix, always run the fixed test case AND the 1–2 most closely related test cases as a lightweight regression check.

### Flaky Test Handling

Automated tests fail intermittently due to timing, animation delays, or network latency — not actual bugs. Signs of flakiness: test passes on retry without code changes, failure inconsistent across runs. Rule: if a test fails twice in a row with identical actual result → real bug. If failure varies between runs → mark as `skip` with note "Flaky — requires investigation" and do not create bug ticket until pattern confirmed.

### Headed vs Headless Decision

OAuth flows (LINE, Google, Facebook) cannot be reliably automated headless due to popup blocking and CORS restrictions. Always use headed + manual pause for third-party OAuth steps. Mark as `blocked` if no test account is available. Headless is 2–3× faster than headed for the same test suite — always default headless, headed only when necessary.

### Evidence Quality

Screenshots alone are insufficient for engineers to reproduce bugs. Always capture all three:

1. **Screenshot** at failure point — shows visual state
2. **Console errors** — JS exceptions reveal root cause (e.g., undefined property access)
3. **Network requests** — 4xx/5xx responses reveal API failures not visible in UI

The combination eliminates "works on my machine" responses and reduces back-and-forth by 60–80%.

### Bug Dedup Threshold

Create new ticket only when confidence < HIGH. Duplicate noise wastes engineering time more than missed bugs — a developer triaging 10 duplicate tickets for the same root cause loses 30–60 minutes. When in doubt, add a comment to the existing ticket instead.

### Key Metrics

- **Pass Rate**: % of executed test cases that pass. Target: ≥ 95% for standard features, 100% for critical paths.
- **Defect Density**: Bugs found per story point. High density (> 2 bugs/SP) → story ACs were unclear or implementation was rushed.
- **Blocked Rate**: % of tests marked `blocked`. > 20% blocked → environment or test data issues, not code issues.
- **Test Execution Velocity**: Test cases per hour. Headless: ~80–120/hour; headed: ~20–40/hour. Use for estimating time before execution.

### Common Failure Modes

| Symptom | Root Cause | Expert Fix |
| --- | --- | --- |
| 90% tests blocked at login | Test account credentials wrong or expired | Verify credentials in Phase 3 pre-flight before running any cases |
| Sheet not updating | View-only link or Google session expired | Re-authenticate in browser; fall back to Jira comment export |
| All tests fail after env deploy | New deployment mid-run or env config change | Wait 5 min for deploy to stabilize; re-run from beginning |
| Same bug reported 3× in same run | Dedup search too narrow (text match only) | Broaden JQL: check summary + labels + status, not just text |
| OAuth tests never pass | Shared test account already linked | Use dedicated QA test account per LINE UID; avoid shared accounts |
