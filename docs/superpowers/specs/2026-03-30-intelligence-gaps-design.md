# Intelligence Gaps Implementation Design

**Date:** 2026-03-30
**Status:** Approved
**Version:** v3 (post 2-round, 4-expert debate)

---

## Problem Statement

atlassian-pm operates as an "Orchestrated Intelligence" system scoring 6.25/10 on an 8-dimension intelligence matrix. Three critical gaps prevent genuine adaptive behavior:

| Gap | Priority | Description |
|-----|----------|-------------|
| G1: Learning Loop | HIGH | `velocity_adjust.py` uses hardcoded formulas; `story-outcomes.jsonl` data is injected as context but never closes the feedback loop |
| G2: Behavioral Adaptation | MEDIUM | No system-level memory that evolves to update agent prompts across sessions |
| G3: Proactive Intelligence | MEDIUM | `monitor/` only notifies stuck issues; never synthesizes board health patterns |

---

## Architecture Overview

```text
story-outcomes.jsonl ──→ [calibrate.py]             ──→ calibration.json
                         (self-gating, atomic write,     (schema_v1, service_tag only,
                          decay-weighted odds ratio,      no PII, team baseline)
                          keyword allowlist at prompt)

board_monitor.py ──────→ [intelligence_analyzer.py]  ──→ insights.json
                          (pure Python, NO LLM,           (structured enums only,
                           threaded async,                 source=ml-derived)
                           reads signal_thresholds
                           from calibration.json)

calibration.json ──┐
insights.json ─────├──→ [start_intelligence_inject.py] ──→ enriched agent prompts
project-config ────┘    (structured stats + signals,
                         agent scope guard,
                         atomic read with fallback)
```

**LLM used in exactly one place:** `calibrate.py` calls Haiku with aggregated stats (never raw Jira text, keywords pass allowlist filter) to synthesize the human-readable `note` field only. `note` is never injected into agent prompts.

---

## Files Changed

### New (6)

| File | Purpose |
|------|---------|
| `scripts/ai/calibrate.py` | Calibration engine |
| `scripts/ai/prompts_calibrate.py` | Haiku prompts for keyword synthesis |
| `scripts/ai/keyword_allowlist.json` | Configurable technical vocabulary for keyword filter |
| `monitor/handlers/intelligence_analyzer.py` | Proactive signal detector (pure Python) |
| `hooks/plugin/session/start_intelligence_inject.py` | Context injector hook |
| `tests/scripts/test_calibrate.py` | Unit tests — calibration engine |
| `tests/hooks/test_start_intelligence_inject.py` | Unit tests — context injector |

### Modified (3)

| File | Change |
|------|--------|
| `scripts/ai/velocity_adjust.py` | Read `calibration.json`; revised formula with derived baseline and cancellation floor |
| `monitor/board_monitor.py` | Threaded `intelligence_analyzer` call; SIGTERM handler; PID lockfile with stale detection |
| `hooks/hooks.json` | Add `SessionStart` + `SubagentStart` hook entries |

**Not changed:** HR rules, SKILL.md files, agent definitions, QG pipeline, existing hooks.

---

## Component 1: Calibration Engine (`scripts/ai/calibrate.py`)

### Self-gating trigger

Open file once to avoid TOCTOU race:

```python
lines = Path(outcomes_path).read_text().splitlines()  # open ONCE
current_line_count = len(lines)
last_count = load_calibration().get("last_calibrated_record_count", 0)
# should_run if ANY condition is true:
should_run = (current_line_count - last_count) >= 10
          or (calibration_age_days > 7)
          or force_flag
```

Callers simply invoke `calibrate.py`; it skips silently if threshold not met.

### Algorithm

1. Open `story-outcomes.jsonl` once, read last 200 lines, parse as `records[]` with `age_days` per record.

2. Compute per `service_tag` group with **decay weighting**:

   ```text
   # Per-record weight (exponential half-life = 60 days)
   w_i = 0.5 ^ (age_days_i / 60)

   # Weighted carry_over_rate  ← REQUIRED, not a simple count
   carry_over_rate = Σ(is_carry_over_i × w_i) / Σ(w_i)

   # decay_weight stored in schema = mean(w_i) for diagnostics only
   decay_weight = mean(w_i)

   # effective_n (accounts for uneven weights)
   effective_n = (Σ w_i)² / Σ(w_i²)
   ```

3. Compute `keyword_risk` using **weighted odds ratio with Laplace α=1**:

   ```text
   # Keywords must pass allowlist filter BEFORE this computation
   # For each keyword k:
   a = Σ(w_i) where carry_over=True  AND keyword k present  (+α=1)
   b = Σ(w_i) where carry_over=False AND keyword k present  (+α=1)
   c = Σ(w_i) where carry_over=True  AND keyword k absent   (+α=1)
   d = Σ(w_i) where carry_over=False AND keyword k absent   (+α=1)
   odds_ratio[k] = (a × d) / (b × c)
   # Include only keywords where odds_ratio > 1.2
   ```

   Each keyword_risk entry carries its own `confidence` level (same effective_n thresholds). See Security section for allowlist.

4. Assign confidence tiers:

   - effective_n ≥ 15 → `"high"` (inject-eligible)
   - effective_n 8–14 → `"medium"` (inject-eligible)
   - effective_n 5–7 → `"low"` (written to file, **NOT injected**)
   - effective_n < 5 → excluded entirely (written to `excluded_groups`)

5. Compute `team_carry_over_baseline` (used by `velocity_adjust.py`):

   ```text
   team_baseline = Σ(carry_over_rate_tag × effective_n_tag) / Σ(effective_n_tag)
   # Falls back to 0.20 only if total records < 15; logs WARNING when fallback active
   ```

6. Build Haiku prompt with **aggregated stats only** — no raw Jira text, no raw keyword lists:

   ```json
   {"[BE]": {"carry_over_rate": 0.22, "n": 34, "top_risk_keywords": ["auth", "migration"]}}
   ```

   If `claude_runner.run_claude()` fails → write `calibration.json` without `note` field; log WARNING; ensure `.tmp` is cleaned up.

7. Write atomically: create `.tmp` with `opener=lambda p,f: os.open(p,f,0o600)` (secure permissions at creation) → write → `os.replace()`.

### calibration.json schema (v1)

```json
{
  "schema_version": 1,
  "generated_at": "2026-03-30T23:00:00",
  "record_count": 87,
  "last_calibrated_record_count": 87,
  "team_carry_over_baseline": 0.27,
  "excluded_groups": {
    "[Video]": {"record_count": 3, "reason": "below_min_n"}
  },
  "service_tags": {
    "[BE]": {
      "carry_over_rate": 0.22,
      "n": 34,
      "confidence": "high",
      "decay_weight": 0.85,
      "keyword_risk": {
        "auth":      {"odds_ratio": 1.4, "confidence": "high"},
        "migration": {"odds_ratio": 1.6, "confidence": "medium"}
      },
      "keyword_method": "weighted_odds_ratio_laplace_alpha1",
      "note": "auth/migration stories carry over more often — surface as risk warning"
    },
    "[FE-Admin]": {
      "carry_over_rate": 0.41,
      "n": 23,
      "confidence": "medium",
      "decay_weight": 0.82,
      "keyword_risk": {
        "integration": {"odds_ratio": 1.3, "confidence": "low"}
      },
      "keyword_method": "weighted_odds_ratio_laplace_alpha1",
      "note": "integration stories consistently carry over — recommend smaller slices"
    }
  },
  "signal_thresholds": {
    "velocity_drop_sigma": 2.0,
    "carry_over_spike_pct": 0.40,
    "stagnant_days_default": 7,
    "stagnant_days_override": {"[FE-Web]": 3},
    "sp_mismatch_pct": 1.5,
    "sp_mismatch_grace_hours": 4
  },
  "calibration_model": "haiku"
}
```

**No per-assignee data.** Aggregation is at `service_tag` level only.

### --prune (atomic, with lock)

```text
1. Acquire fcntl advisory lock on story-outcomes.jsonl
2. Read all lines
3. Keep last 500
4. Write to story-outcomes.jsonl.tmp (mode 0o600)
5. os.replace() → story-outcomes.jsonl
6. Release lock
```

This prevents data loss during concurrent appends from hooks.

---

## Component 2: Proactive Analyzer (`monitor/handlers/intelligence_analyzer.py`)

**Pure Python — zero LLM calls.** Signal detection is deterministic. All thresholds are read from `calibration.json["signal_thresholds"]` at startup — no hardcoded literals in analyzer code.

### Integration with board_monitor.py

```python
# After snapshot is persisted to disk — NOT before
thread = threading.Thread(
    target=intelligence_analyzer.analyze,
    args=(diff, board_snapshot, calibration),
    daemon=True
)
thread.start()
# poll loop continues; analyzer writes insights.json asynchronously
```

**Shutdown:** `board_monitor.py` registers a `SIGTERM` handler that:

1. Signals the analyzer thread (via `threading.Event`)
2. Joins with 3-second timeout
3. Deletes any in-flight `.tmp` file before exit

### 5 Signals

All thresholds loaded from `calibration.json["signal_thresholds"]` at runtime.

| Signal | Threshold (configurable) | TTL | Guard |
|--------|--------------------------|-----|-------|
| `velocity_drop` | `< rolling_mean − velocity_drop_sigma × σ` from `velocity_feed.py` history | 72h | ≥3 sprints in feed |
| `carry_over_spike` | `> carry_over_spike_pct` of sprint items | 72h | ≥5 items in sprint |
| `wip_breach` | Either WIP-limited column exceeds limit for **>2 consecutive poll cycles** | 24h | — |
| `stagnant_issue` | In Progress > `stagnant_days_default` days, no `updated` change in snapshot diff | 24h | Per-tag override via `stagnant_days_override` |
| `sp_mismatch` | Subtask sum > `sp_mismatch_pct × parent_sp` AND parent already In Progress AND parent transitioned to In Progress > `sp_mismatch_grace_hours` ago | 24h | Grace period avoids execution-phase decomposition false positives |

### Dedup keys (per signal type)

- `velocity_drop`: `(signal_type, service_tag, sprint_id)`
- `carry_over_spike`: `(signal_type, service_tag, sprint_id)` — NOT a static key; re-fires after TTL expires
- `wip_breach`: `(signal_type, column_name)`
- `stagnant_issue`: `(signal_type, issue_key)`
- `sp_mismatch`: `(signal_type, issue_key)`

### insights.json output (structured only — no narrative)

```json
[
  {
    "signal": "carry_over_spike",
    "severity": "warning",
    "service_tag": "[BE]",
    "sprint_id": 42,
    "metric_value": 0.55,
    "baseline_value": 0.22,
    "delta_pct": 150,
    "affected_keys": ["{{PROJECT_KEY}}-234", "{{PROJECT_KEY}}-235"],
    "generated_at": "2026-03-30T09:00:00",
    "expires_at": "2026-04-02T09:00:00",
    "source": "ml-derived"
  }
]
```

### Eviction policy (max 10 active)

1. Remove TTL-expired entries first
2. If still >10, evict oldest by `generated_at`

### File write

Atomic: open `.tmp` with `opener=lambda p,f: os.open(p,f,0o600)` → write → `os.replace()`.

---

## Component 3: Context Injector (`hooks/plugin/session/start_intelligence_inject.py`)

### Trigger

`SessionStart` + `SubagentStart`.

**Agent identification:** read `agent_name` field from stdin JSON at `SubagentStart`. If field absent → no injection (safe default); log WARNING so the gap is observable.

### Agent scope (opt-in, hardcoded list — update when new agents require calibration)

| Agent | What it receives |
|-------|-----------------|
| `estimation-calibrator` | calibration stats (high/medium confidence only) |
| `risk-forecaster` | calibration stats + active signals |
| `story-writer` | calibration stats (keyword risk as WARNING — `note` field excluded) |
| `sprint-planner` | active signals only |
| all others | no injection |

### Cold start behavior

- `calibration.json` missing → inject: `"Calibration not yet run. Run: python3 scripts/ai/calibrate.py --force"`
- `calibration.json` age >7 days → inject with staleness note (same threshold as trigger in calibrate.py — keep in sync)
- `insights.json` missing → skip signals silently (no error)

### Injected block format

```text
## Intelligence Context
Calibration (n=87, 2026-03-30, schema_v1, team_baseline=27%):
  [BE]       carry_over=22% (n=34, conf=high) | risk: auth×1.4 migration×1.6
  [FE-Admin] carry_over=41% (n=23, conf=medium) | risk: integration×1.3 (conf=low, advisory)
  [FE-Web]   carry_over=15% (n=18, conf=medium) | no keyword flags

Active Signals (2):
  WARN carry_over_spike  [BE] 55% vs baseline 22% (+150%) sprint=42 keys: {{PROJECT_KEY}}-234 {{PROJECT_KEY}}-235
  WARN stagnant_issue    {{PROJECT_KEY}}-219 In Progress 6d

Advisory: statistical patterns from story-outcomes.jsonl. Surface as risk context only.
Do NOT auto-adjust SP estimates. Note fields and narrative content are excluded.
```

**Security:** this block is informational metadata — it is NOT a security control. Security is provided by the keyword allowlist (see below) and the structured-only injection policy. The advisory note is for human readers, not LLM instruction enforcement.

---

## Component 4: velocity_adjust.py Update

### Revised formula

```python
trend_adj = max(trend_pct * 0.5, -15)  # unchanged

# Calibration adjustment — requires calibration.json
cal_adj = 0.0
if calibration and tag in calibration["service_tags"]:
    entry = calibration["service_tags"][tag]
    if entry.get("confidence") in ("high", "medium"):
        rate = entry["carry_over_rate"]
        # Use team-derived baseline, NOT hardcoded 0.20
        baseline = calibration.get("team_carry_over_baseline", 0.20)
        raw_cal = (rate - baseline) * 50
        cal_adj = max(min(raw_cal, 10.0), -10.0)  # symmetric clamp ±10%

# Signal cancellation floor:
# When both signals point to the same risk direction, cal_adj should reinforce,
# not cancel. Cap cal_adj's offset of trend_adj at 50% in the same direction.
if trend_adj < 0 and cal_adj > 0:
    cal_adj = min(cal_adj, abs(trend_adj) * 0.5)

# Combined cap ±20%
adjustment_pct = max(min(trend_adj + cal_adj, 20.0), -20.0)
```

**Fallback:** if `calibration.json` is absent, `tag` not found, or `confidence` is "low" → `cal_adj = 0.0` (passthrough, no error).

---

## Security Design

### Keyword allowlist (critical control)

Keywords in `story-outcomes.jsonl` originate from story summaries (user-controlled content). Before any keyword enters the Haiku prompt, it must pass the allowlist filter:

```text
keyword_allowlist.json — configurable, not hardcoded:
["auth", "migration", "integration", "payment", "webhook", "refactor",
 "performance", "cache", "search", "notification", "upload", "export", ...]
```

**Filter location:** applied in `calibrate.py` when building the Haiku prompt payload, NOT at extraction time (to preserve full keyword data in `story-outcomes.jsonl` for future use). Tokens not in allowlist are silently dropped from the prompt payload.

**Allowlist maintenance:** add domain terms via PR to `keyword_allowlist.json` — does not require code changes.

### PID lockfile (stale detection required)

```text
On board_monitor startup:
1. Read ATLASSIAN_PM_MONITOR_ACTIVE PID file (if exists)
2. Check os.kill(stored_pid, 0) — if process alive → exit (already running)
3. If process dead (ProcessLookupError / PermissionError) → log WARNING
   "Stale lock detected (pid=N). Previous instance terminated abnormally. Clearing."
   → delete lockfile → continue startup
4. Write current PID to lockfile
5. On exit: delete lockfile
```

### Injection security model

| Layer | Control |
|-------|---------|
| Jira free text → story-outcomes.jsonl | No restriction (preserve data quality) |
| story-outcomes.jsonl → Haiku prompt | **Keyword allowlist** (configurable file) |
| calibration.json `note` field | NOT injected into agent prompts |
| insights.json fields | Structured only (signal enum, numbers, issue keys) |
| inject_context() output | Human-readable metadata; no security enforcement claim |

No per-assignee data stored anywhere.

---

## Data Files Summary

| File | Location | Written by | Read by | Integrity |
|------|----------|-----------|---------|-----------|
| `calibration.json` | `CLAUDE_PLUGIN_DATA/` | `calibrate.py` | `velocity_adjust.py`, inject hook | atomic `os.replace()`, mode 0o600 at creation |
| `insights.json` | `CLAUDE_PLUGIN_DATA/` | `intelligence_analyzer.py` | inject hook, `/status` skill | atomic `os.replace()`, mode 0o600 at creation |
| `story-outcomes.jsonl` | `CLAUDE_PLUGIN_DATA/` | existing hooks | `calibrate.py` | append-only; prune with fcntl lock + atomic replace |
| `keyword_allowlist.json` | `scripts/ai/` | developer (PR) | `calibrate.py` | version-controlled |

**Retention:** `story-outcomes.jsonl` capped at 500 records by `--prune`.
**gitignore:** `calibration.json` and `insights.json` must not be committed.

---

## hooks.json Additions

```json
{
  "SessionStart": [
    {
      "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/start_intelligence_inject.py",
      "timeout": 10
    }
  ],
  "SubagentStart": [
    {
      "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/start_intelligence_inject.py --subagent",
      "timeout": 10
    }
  ]
}
```

---

## Testing Strategy

| Component | Test cases |
|-----------|-----------|
| `calibrate.py` | cold start; <5 records; n=15 threshold; decay formula boundary values; odds ratio with α=1; team_baseline derivation; fallback to 0.20; allowlist filter; atomic write; TOCTOU-safe trigger; haiku failure path |
| `intelligence_analyzer.py` | each signal fires/doesn't fire at threshold; signals read from calibration.json (not hardcoded); dedup per signal type; eviction; SIGTERM teardown; stale .tmp cleanup |
| `start_intelligence_inject.py` | missing calibration; stale calibration; low-confidence entries excluded; agent scope guard; SubagentStart agent_name absent; cold start message |
| `velocity_adjust.py` | absent calibration fallback; team_baseline derived; signal cancellation floor at boundary; symmetric clamp |

---

## Out of Scope (document intentional omissions)

- **Per-assignee carry_over tracking** — psychological safety violation; team-level only
- **SP auto-inflation** — corrupts velocity; risk warning only
- **LLM calls in monitor daemon** — prompt injection risk; pure Python signals only
- **Skill redirect tuning** — not the bottleneck (YAGNI)
- **`blocked_issue` signal** — blocked status in Jira is frequently stale; high false-positive rate; revisit when status discipline improves
- **`ready_for_qa_queue` signal** — requires QA capacity modeling outside this spec's domain; separate signal spec is the correct vehicle
- **`stagnant_issue` re-alert suppression** — daily re-alert on persistent issues is intentional; operators who find it noisy should increase `stagnant_days_override`
- **Feedback loop full elimination** — decay weighting reduces recency bias; circularity is a known limitation, not fully mitigated in v3
