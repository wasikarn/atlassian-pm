---
name: qa-full
description: |
  Triggers: "qa full", "create and run testplan", "QA end-to-end", "ทดสอบ story ครบ", "QA ครบ"
  Orchestrates: create-testplan → execute-testplan
model: sonnet
argument-hint: "<issue-key> [--env staging|production] [--headed] [--rerun-failed]"
---

# /qa-full

Orchestrates: `create-testplan` → `execute-testplan`

## Steps

### Step 0 — Guard: Check Existing Test Plan

Before creating anything, check if a `[QA]` sub-task already exists for the story:

```bash
acli jira issue list --jql "parent = <issue-key> AND summary ~ \"[QA]\" AND issuetype = Sub-task" -y
```

**If `[QA]` sub-task found** (e.g., `{{PROJECT_KEY}}-XXXX`):

Present the user with 3 options:

> Test plan already exists: **{{PROJECT_KEY}}-XXXX** — "[QA] …"
>
> (A) **Execute existing plan** — run execute-testplan on {{PROJECT_KEY}}-XXXX as-is
> (B) **Update + execute** — update test plan for current AC, then execute
> (C) **Create new plan** — create a fresh [QA] sub-task (use if scope changed significantly)

Wait for user choice before proceeding:

- **(A)** → skip to Step 3 using the existing sub-task key
- **(B)** → invoke `atlassian-pm:create-testplan` with `--update {{PROJECT_KEY}}-XXXX`, then Step 3
- **(C)** → proceed to Step 1

**If no `[QA]` sub-task found** → proceed to Step 1.

> **Why this matters:** Running qa-full twice on the same story without a guard creates duplicate [QA] sub-tasks, polluting the issue hierarchy and making it unclear which test plan is authoritative. The guard turns qa-full into an idempotent operation — safe to re-run for regression cycles.

### Step 1 — Create Test Plan

Use the Skill tool to invoke `atlassian-pm:create-testplan` with `$ARGUMENTS`.

→ Produces `[QA]` Sub-task with embedded test plan linked to the story.
→ Wait for skill to complete and confirm `[QA]` Sub-task key (e.g., `{{PROJECT_KEY}}-XXXX`).

### Step 2 — Confirm Execute

Ask: "Test plan created (`{{PROJECT_KEY}}-XXXX`). Run execute-testplan against **staging** now?"

→ If yes (or no `--env` specified): proceed with `--env staging`
→ If user specifies `--env production`: warn "⚠️ Running against production — confirm?" before proceeding
→ If no: exit after test plan creation

### Step 3 — Execute Test Plan

> **Gate:** Confirm a `[QA]` subtask key is available (from Step 1 creation or Step 0 existing plan). If create-testplan failed without producing a key, STOP and show: "create-testplan did not complete — resolve before executing."

Use the Skill tool to invoke `atlassian-pm:execute-testplan` with the `[QA]` sub-task key confirmed in Steps 0/1 (e.g., the key from "Test plan created (`{{PROJECT_KEY}}-XXXX`)") and resolved `--env` flag.

→ Pass through any additional flags (`--headed`, `--rerun-failed`, `--dry-run`) from `$ARGUMENTS`.
→ Results written back to Google Sheet, bugs created for failures, summary posted to Jira.

## Use Cases

| Scenario | Command | Behavior |
| --- | --- | --- |
| First QA run on a story | `/qa-full {{PROJECT_KEY}}-3282` | Create plan → confirm → execute on staging |
| Regression after a fix | `/qa-full {{PROJECT_KEY}}-3282 --rerun-failed` | Guard finds existing plan → option A/B → rerun only failed cases |
| Production smoke test | `/qa-full {{PROJECT_KEY}}-3282 --env production` | Guard check → execute on production (with warning) |
| OAuth / LINE test | `/qa-full {{PROJECT_KEY}}-3282 --headed` | Guard check → execute with visible browser |
| Plan only, no run | `/qa-full {{PROJECT_KEY}}-3282` → answer "No" at Step 2 | Create plan, exit |

## 🎓 Domain Expert Notes

### Idempotency in Test Orchestration (ISTQB)

A test orchestration command that is **not idempotent** — one that creates duplicate artifacts when run twice — is an anti-pattern. In ISTQB Test Management, the test plan is a versioned artifact: it has a lifecycle (draft → approved → executed → closed). Re-running QA should mean executing the same plan, not creating a new one. The guard step enforces this — qa-full is safe to re-run at any sprint cycle without manual cleanup.

### Regression Testing vs Re-testing (ISTQB distinction)

- **Re-testing**: run the same test case that previously failed, after a fix — verifying the fix works.
- **Regression testing**: run the *full* test suite (or a risk-weighted subset) to ensure the fix didn't break something else.

`--rerun-failed` is a **re-test** cycle. A fresh `/qa-full` on the same story (option C or a new sprint) is a **regression** cycle. Both are valid — the guard step enables both without duplication.

### Test Plan as a Living Document

The option B path ("Update + execute") supports the IEEE 829 concept of a **living test plan**: as ACs evolve during a sprint, the test plan must evolve with them. A test plan that no longer reflects current ACs is worse than useless — it provides false confidence. Running create-testplan with `--update` re-diffs the ACs and adds/removes/modifies test cases without losing prior execution results.
