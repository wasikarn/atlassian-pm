# Subtask Design Patterns

Shared reference for `/analyze-story` and `/create-story`. Load when designing sub-tasks.

## What Each Agent Must Discover

| Agent | Must Find |
|-------|-----------|
| Backend | Models/Migrations path, Controllers pattern, Routes file, Config enums (any enum to extend?), Auth middleware on similar routes, Existing similar implementation as REF |
| Frontend | Page dir structure, Service base pattern (`ApiBaseService`?), OAuth/auth lib, Shared UI components (dialogs, icons, layouts) with exact filenames |
| Shared/Config | `.env` variables consumed by feature, Types/interfaces, Error handling patterns |

## Critical Validation Rules

- Validate every filename with Glob — don't assume (typos exist in real codebases, e.g., `account-layoyt.component.tsx`)
- Config enums that need new values → include as MODIFY in scope
- Auth middleware: which routes require `auth:publicApi`? Which are public?
- Find at least 1 REF pattern per subtask to guide developer

## Scope Table Format

Single Action | File table per subtask:

- `CREATE` — new file to create from scratch
- `MODIFY` — existing file to add/change code
- `REF` — existing file developer reads as pattern guide (no changes — just follow the pattern)
- **Minimum 1 REF row per subtask** — never leave developer without a pattern reference

## AC Specificity Requirements

Tech Lead level — reference concrete findings from Codebase Exploration:

- Reference actual method names from exploration: `LineAuthStrategy.handleCallback()`
- Specify exact HTTP endpoints + status codes: `POST /v2/notification/line-accounts → 201 or 409`
- Specify data contracts: `{ line_uid, display_name, avatar_url, access_token }`
- Specify error UI: toast color + exact error message text
- Specify env vars if consumed by new code: `LINE_MESSAGING_API_CHANNEL_ACCESS_TOKEN`

## Config/Enum Awareness

- New feature type → check if config enum needs a new value (add as MODIFY to scope)
- New unique constraint → specify explicitly in migration AC
- Middleware → document which middleware applies to each new route in AC

## Alignment Check

> **🟢 AUTO** — Verify programmatically. Auto-fix misalignment. Escalate only if unfixable.

- [ ] Sum of sub-tasks = Complete Story?
- [ ] No gaps? No scope creep?
- [ ] File paths exist? (validate with Glob)
- [ ] **VS integrity maintained?** (subtasks complete the slice, not horizontal split)

If any check fails → auto-adjust subtask scope/design → re-check. Escalate to user only if gap cannot be resolved automatically.

## Quality Gate — Subtasks

> **🟢 AUTO** — Score → auto-fix → re-score. Escalate only if still < 90% after 2 attempts.
> HR1: DO NOT create subtasks in Jira without QG ≥ 90%.

For each subtask ADF JSON in `{{artifacts_dir}}/`:

1. **Delegate to quality-gate agent:** `Agent(name: "quality-gate")` — pass subtask JSON path + issue type `subtask`. Receives: `{score, status, checks_failed[], auto_fixable}`.
2. If `status = PASS` → proceed
3. If `status = FAIL` and `auto_fixable = yes` → apply fixes inline → re-invoke quality-gate (max 1 re-invoke)
4. If still FAIL → escalate to user with specific check failures
5. Only proceed to next phase when ALL subtasks pass QG

> Report: `Technical X/5 | Subtask Quality X/5 | Overall X%`
