# P10 — `/sandbox` Mode Evaluation Report

**Date:** 2026-03-23
**Claude Code Version:** 2.1.81
**Evaluator:** automated (subagent)

## Summary

**Result: UNAVAILABLE — Skip P10**

`/sandbox` as a session-scoped slash command does not exist in Claude Code CLI v2.1.81.

## Findings

### `claude --help` output (relevant flags)

```
--allow-dangerously-skip-permissions    Enable bypassing all permission checks as an option,
                                        without it being enabled by default. Recommended only
                                        for sandboxes with no internet access.
--dangerously-skip-permissions          Bypass all permission checks. Recommended only for
                                        sandboxes with no internet access.
```

No `/sandbox` slash command is listed. No session-scoped permission-reduction mode is exposed via CLI.

### Changelog search

The term "sandbox" appears in `~/.claude/cache/changelog.md` but refers exclusively to:

- `sandbox.filesystem.allowWrite` — a config file setting (desktop app)
- `/sandbox` — a **settings dialog tab** in the desktop GUI (not a slash command)
- `sandbox.enabled`, `sandbox.excludedCommands`, `sandbox.enableWeakerNetworkIsolation` — desktop app config keys

None of these are a session-scoped CLI slash command equivalent.

### What `--dangerously-skip-permissions` does

This flag **bypasses ALL permission checks** — it disables every write/execute guard in the session. It is the opposite of a permission-reduction sandbox; it is a permission-elimination escape hatch. Using it in production automation is unsuitable.

## Decision

**Skip P10 implementation.**

The `--dangerously-skip-permissions` flag is not equivalent to a `/sandbox` session-scoped permission reduction mode:

| Aspect | `/sandbox` (hypothetical) | `--dangerously-skip-permissions` |
|---|---|---|
| Scope | Reduces write tool permissions | Eliminates ALL permission checks |
| Safety | Narrows attack surface | Eliminates safety guards |
| Production use | Suitable | Unsuitable |

## Recommendation

Re-evaluate P10 when upgrading Claude Code beyond v2.1.81. Check for:

1. A `/sandbox` slash command in `claude --help`
2. A session-scoped `--sandbox` or `--restrict-tools` flag
3. Release notes mentioning "permission reduction" or "session sandbox mode"
