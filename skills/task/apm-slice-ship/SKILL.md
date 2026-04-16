---
name: apm-slice-ship
context: fork
agent: general-purpose
x-compatibility: [atlassian-cache, mcp-atlassian, acli, gh-cli]
argument-hint: "[issue-key]"
effort: medium
allowed-tools: Read, Bash, mcp__mcp-atlassian__jira_get_issue, mcp__mcp-atlassian__jira_get_transitions, mcp__mcp-atlassian__jira_transition_issue, mcp__mcp-atlassian__jira_add_comment, mcp__mcp-atlassian__jira_update_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_get_issue, mcp__plugin_atlassian-pm_atlassian-cache__cache_invalidate
description: |
  Guide dev/QA through the per-slice ship workflow (TaThep ship-per-merge convention, 2026-04-16).
  Enforces flag-off deploy → observability smoke → QA verify → PM release gate in 5 phases.
  Skill checks: `vs-*` label, parent Epic ADR reference, `.flags.yaml` registration, coverage ≥80%, rollback runbook.

  Triggers: "ship slice", "slice ship", "vs ship", "ship per merge", "flag off deploy", "dark deploy slice", "slice-ship {{PROJECT_KEY}}-XXX", "ship {{PROJECT_KEY}}-XXX dark"
  Use when: slice PR merged to trunk and you need to walk the ship → release gates (flag off then PM-gated flag on)
  Do NOT use for: plain QA handoff before merge (use apm-ship-to-qa); full release planning (use apm-plan-release)
---

# /atlassian-pm:apm-slice-ship

**Role:** Dev + QA + PM per-phase gates · **Output:** Jira comment per phase + transitions + release decision

**Convention reference:** `feedback_ship_per_merge_convention.md` (binding TaThep rules, 2026-04-16) — 13 consensus rules + 8 Team Lead verdicts. Keys used below: C1-C13, D1-D8.

## Pre-flight Checks (Phase 0)

> Run BEFORE entering ship pipeline. Any FAIL → stop, ask user to remediate.

| # | Check | Source | Fail action |
| --- | --- | --- | --- |
| P0.1 | Ticket has `vs-*` label (e.g. `vs1-skeleton`, `vs2-multi-owner`) | `jira_get_issue` labels | Ask user to add VS label; abort if unclear which slice this is |
| P0.2 | Parent Epic links an ADR (Architecture Decision Record) | Epic description or Coverage Matrix | Ask dev to author ADR (C10) before shipping |
| P0.3 | Flag registered in repo `.flags.yaml` (name `feat/{epic-key}/s{slice-num}`) | `grep -r "feat/{epic}" .flags.yaml` | Block; require flag entry before merge (C5, C6) |
| P0.4 | Coverage ≥80% on merged PR | CI metadata (GitHub check `coverage` or repo `.ci/coverage.json`) | <80% → route to manual-gate (staging + QA sign-off) per D1 |
| P0.5 | Rollback runbook link in PR description | `gh pr view --json body` grep `runbook` or `rollback` | Ask dev to add runbook link before ship (C4) |
| P0.6 | Contract tests green (Pact) for paired BE/FE/AI slices | CI check `contract-test` | Block until green (C9) |

**Output:** Single `[phase-0]` comment on Jira with check matrix. Proceed only if all PASS (or user explicitly overrides for carve-outs, see below).

### Carve-out Services (manual-gate, not auto)

Per D5, these services require manual CI approval even when Phase 0 passes:

- `tathep-ai-agent-python` — LangGraph graph state, needs drain
- `tathep-video-processing` — long-running jobs, queue drain required

For carve-outs, skip the auto-deploy path in Phase 1 and route directly to staging + QA sign-off lane. Re-audit carve-out list Day 60 post-pilot.

## Phases

### Phase 1 — Deploy to prod (flag OFF)

> **C1 / C2 / D1** — ship ≠ release; trunk stays deployable; flag OFF so no user exposure.

Decision gate:

- Coverage ≥80% + smoke + contract green → **auto path**: merge to trunk triggers auto-deploy pipeline (dev → staging → prod canary 5% → 25% → 100%).
- Coverage <80% OR carve-out service → **slower lane**: deploy to staging; wait for QA smoke sign-off; manual-approve prod deploy.

Actions:

1. Run `gh pr view --json state,mergedAt` — confirm merged to trunk.
2. Post `[phase-1]` comment on Jira: `Shipped to prod (flag off)` + deploy pipeline URL + flag name.
3. Transition ticket → `Shipped (flag-off)` (or keep current `In Review` if workflow state not yet added — comment documents the intent).
4. Add label `vs-shipped-dark`.

### Phase 2 — Observability smoke (30-min post-deploy watch)

> **C8** — error rate alert, p99 latency, structured logs, trace IDs, rollback runbook must be live.

Actions:

1. Watch for 30 minutes. Grep metrics dashboard link from Epic's Technical Reference.
2. Validate: error rate ≤ baseline + 2σ; p99 latency within SLO; no trace-ID gaps in structured logs.
3. Post `[phase-2]` comment: either `Smoke pass — no regression` or `Smoke FAIL — rolled back; see runbook`.
4. If FAIL → rollback via flag-off (already off; confirm deploy reverted) or hotfix; escalate per circuit-breaker rule D8 (SRE freezes unilaterally).

### Phase 3 — QA verification on prod with flag OFF (dark)

> **D6** — QA owns smoke + epic-boundary tests; dev owns unit + contract.

Actions:

1. QA runs dark-path tests on prod (feature code present, flag off — verify no side effects in legacy path).
2. QA validates: existing flows unchanged, no new errors in logs, feature toggle mechanism works (flip on/off in staging without crash).
3. Post `[phase-3]` comment: `QA dark verify pass — ready for PM release decision` or failure notes.
4. Transition ticket → `Ready for Release` (or equivalent "awaiting PM flag-on" state).

### Phase 4 — PM approves flag-on toggle (RELEASE gate)

> **C12** — PM owns flag EXPOSURE decision; engineers merge freely, but release = PM's call.

Actions:

1. PM reviews: business value delivered, risk acceptable, user-facing release notes drafted (C11 — 2-tier notes: auto per-merge + user-facing per epic milestone).
2. PM runs flag-on via Unleash (or configured flag infra per O1) — start at canary ring (e.g. `tathep-admin` users = ring-1 per O5).
3. Monitor for 24h at ring-1. If healthy → expand ring.
4. Post `[phase-4]` comment: `PM approved flag-on — released to {ring}` + release notes link.
5. Add label `vs-released`. Remove `vs-shipped-dark`.

### Phase 5 — Update Jira ticket → `Released` (or `Done`)

Actions:

1. Transition ticket → `Released` (preferred) or `Done` (if workflow unchanged — then reinterpret `Done` = `Released` per templates-core guidance).
2. Post `[phase-5]` comment summary: deploy timestamp, flag-on timestamp, exposure %, user-facing release notes URL.
3. Schedule flag cleanup: 30-day TTL starts now (C5) — flag moves from `active` → `released` status in `.flags.yaml`.
4. `cache_invalidate(issue_key)`.

## Observability Smoke Checklist (Phase 2 detail)

- [ ] Error rate: new / baseline < 1.2× (99th percentile)
- [ ] p99 latency: within SLO band (per Epic's Technical Reference)
- [ ] Structured logs: trace ID present on every request
- [ ] Rollback runbook link: reachable, current
- [ ] Flag toggle test: flip on/off in staging without process restart

## Flag Lifecycle Summary

```text
[registered in .flags.yaml]  →  active  →  released  →  scheduled-for-removal  →  removed
      (Phase 0 pre-ship)       (Phase 1 ship)  (Phase 4 release)   (>30 days post-release)   (dead code purge)
```

CI fails the build if any flag past `expiry` date (C5). See [flags-yaml-template.yaml](../../../references/flags-yaml-template.yaml).

## Examples

### Good

```text
/apm-slice-ship {{PROJECT_KEY}}-196                    # walk Phase 0-5 for slice ticket
/apm-slice-ship {{PROJECT_KEY}}-197 --dry-run          # pre-flight only, no transitions
/apm-slice-ship {{PROJECT_KEY}}-200 --carve-out        # manual-gate lane for AI-agent/video services
```

### Bad

```text
/apm-slice-ship                           # no issue key — cannot run pre-flight
/apm-slice-ship {{PROJECT_KEY}}-42                     # parent Task not a slice (no vs-* label) — abort P0.1
/apm-slice-ship {{PROJECT_KEY}}-42 --skip-coverage     # not valid; coverage gate enforced by D1 + D7
```

## Edge Cases

| Situation | Handling |
|-----------|---------|
| `vs-*` label missing | Abort P0.1; ask user which slice this ticket represents |
| Flag not in `.flags.yaml` | Abort P0.3; direct to `references/flags-yaml-template.yaml` |
| Coverage <80% | Route to slower lane (staging + QA sign-off); not a FAIL |
| Carve-out service (AI-agent / video) | Manual-gate lane regardless of coverage; re-audit Day 60 |
| Paired-epic sibling not merged | Surface in P0 comment; decide: ship alone with regression AC or wait |
| Flag past `expiry` in registry | CI already failed the build; require `expiry` extension approval or remove flag |
| Rollback runbook stale | Block Phase 1 until updated |

## References

- Binding decision: `~/.claude/memory/feedback_ship_per_merge_convention.md` (13 rules + 8 verdicts)
- Vertical slice guide: [vertical-slice-guide.md](../../../references/vertical-slice-guide.md) (Ship Strategy section)
- Flags template: [flags-yaml-template.yaml](../../../references/flags-yaml-template.yaml)
- Jira workflow convention: [templates-core.md](../../../references/templates-core.md) (Jira Workflow — TaThep ship-per-merge)
- Epic slicing plan: [templates-epic.md](../../../references/templates-epic.md) (Slicing Plan section)

## Domain Expert Notes

Ship-per-merge is not CI/CD theater — it's a discipline contract between engineering (who merge freely to trunk, flag OFF) and product (who owns exposure via flag-on). The key insight from the TaThep 4-role debate: "deploy" and "release" are two events, not one. Collapsing them forces batch releases (weeks to prod) or unsafe exposure (users see half-built features). Separating them gives DORA Elite velocity without YOLO risk.

The 30-day flag TTL (C5) is a garbage-collection contract — without it, flags become permanent branches in production code, doubling test matrix forever. Owner field is named so the cleanup lands on a human, not a team queue.

Coverage ≥80% as auto-deploy privilege (D7) is the carrot for test discipline; the slower lane (staging + QA sign-off) is the stick for skipping tests. Both paths ship; only the fast path trusts the author.
