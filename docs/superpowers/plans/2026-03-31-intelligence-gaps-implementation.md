# Intelligence Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 3 intelligence gaps (G1 Learning Loop, G2 Proactive Intelligence, G3 Context Injection) by adding calibrate.py, intelligence_analyzer.py, and a context injector hook.

**Architecture:** `story-outcomes.jsonl` → `calibrate.py` (decay-weighted stats) → `calibration.json`; `board_monitor.py` → `intelligence_analyzer.py` (pure Python signals) → `insights.json`; both files → `start_intelligence_inject.py` → enriched agent prompts at SessionStart/SubagentStart.

**Tech Stack:** Python 3.x stdlib only (json, fcntl, threading, os, math, re, datetime, signal). Haiku via `scripts/ai/claude_runner.py` (one call in calibrate.py only). pytest for tests.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `scripts/ai/keyword_allowlist.json` | CREATE | Allowlist of safe keywords for Haiku prompt |
| `scripts/ai/prompts_calibrate.py` | CREATE | Haiku prompt builder for note synthesis |
| `scripts/ai/calibrate.py` | CREATE | Calibration engine — decay-weighted odds ratio |
| `monitor/handlers/intelligence_analyzer.py` | CREATE | Pure Python signal detector (5 signals) |
| `hooks/plugin/session/start_intelligence_inject.py` | CREATE | Context injector hook |
| `tests/scripts/test_calibrate.py` | CREATE | Unit tests — calibration engine |
| `tests/monitor/__init__.py` | CREATE | Make tests/monitor a package |
| `tests/monitor/test_intelligence_analyzer.py` | CREATE | Unit tests — signal detector |
| `tests/hooks/test_start_intelligence_inject.py` | CREATE | Unit tests — context injector |
| `scripts/ai/velocity_adjust.py` | MODIFY | Add calibration-sourced adjustment signal |
| `monitor/board_monitor.py` | MODIFY | Threading, PID lockfile, SIGTERM, analyzer dispatch |
| `hooks/hooks.json` | MODIFY | Add SessionStart + SubagentStart entries |
| `.gitignore` | MODIFY | Exclude calibration.json + insights.json |

**Data schema note:** `story-outcomes.jsonl` records (written by `story_outcome_record.py`) use `service_tag` WITHOUT brackets (e.g. `"BE"`, `"FE-Admin"`) and `outcome: "completed" | "carry_over"`. `calibrate.py` normalizes tags to bracket form `[BE]` to match `project-config.json` convention.

---

## Task 1: Static files — keyword_allowlist.json + prompts_calibrate.py

**Files:**
- Create: `scripts/ai/keyword_allowlist.json`
- Create: `scripts/ai/prompts_calibrate.py`

- [ ] **Step 1: Create keyword_allowlist.json**

```json
[
  "auth", "migration", "integration", "payment", "webhook",
  "refactor", "performance", "cache", "search", "notification",
  "upload", "export", "import", "report", "dashboard",
  "analytics", "scheduler", "queue", "batch", "sync",
  "permission", "role", "approval", "workflow", "email",
  "video", "transcoding", "streaming", "encoding", "storage",
  "database", "index", "query", "transaction", "constraint",
  "deployment", "config", "environment", "logging", "monitoring",
  "testing", "validation", "serializer", "endpoint", "middleware"
]
```

- [ ] **Step 2: Create prompts_calibrate.py**

```python
"""Haiku prompts for calibration note synthesis in calibrate.py."""


def build_calibrate_prompt(service_tags: dict) -> str:
    """Build Haiku prompt with aggregated stats only — no raw Jira text.

    Input service_tags already filtered by confidence (high/medium only).
    Keyword lists are already allowlist-filtered before this function is called.
    """
    lines = ["For each service tag below, write one sentence (≤20 words) describing"]
    lines.append("the main carry-over risk pattern. Return JSON: {\"[TAG]\": \"sentence\"}.")
    lines.append("Base your response ONLY on the statistics provided — do not invent patterns.")
    lines.append("")
    lines.append("Stats:")
    for tag, data in service_tags.items():
        if data.get("confidence") not in ("high", "medium"):
            continue
        rate_pct = int(data["carry_over_rate"] * 100)
        n = data["n"]
        risk_kws = list(data.get("keyword_risk", {}).keys())[:3]
        kw_str = f", risk keywords: {risk_kws}" if risk_kws else ""
        lines.append(f"  {tag}: carry_over={rate_pct}% (n={n}{kw_str})")
    return "\n".join(lines)
```

- [ ] **Step 3: Commit**

```bash
git add scripts/ai/keyword_allowlist.json scripts/ai/prompts_calibrate.py
git commit -m "feat(intelligence): add keyword allowlist + calibrate prompts"
```

---

## Task 2: Calibration engine — TDD

**Files:**
- Create: `tests/scripts/test_calibrate.py`
- Create: `scripts/ai/calibrate.py`

- [ ] **Step 1: Write failing tests**

Create `tests/scripts/test_calibrate.py`:

```python
"""Tests for scripts/ai/calibrate.py."""
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai"))
import calibrate


def _make_record(service_tag, outcome, age_days=0, summary="fix auth bug"):
    ts = (datetime.now(UTC) - timedelta(days=age_days)).isoformat()
    return json.dumps({
        "ts": ts, "sprint_id": "1", "sprint_name": "S1",
        "issue_key": "{{PROJECT_KEY}}-1", "summary": summary,
        "issuetype": "Story", "estimated_sp": 3,
        "assignee": None, "service_tag": service_tag,
        "outcome": outcome, "final_status": "Done",
    })


def _write_outcomes(tmp_path, records):
    path = tmp_path / "story-outcomes.jsonl"
    path.write_text("\n".join(records) + "\n")
    return path


# ── _weight ────────────────────────────────────────────────────────────────────

def test_weight_age_zero_is_one():
    assert calibrate._weight(0) == pytest.approx(1.0)


def test_weight_age_60_is_half():
    assert calibrate._weight(60) == pytest.approx(0.5)


def test_weight_age_120_is_quarter():
    assert calibrate._weight(120) == pytest.approx(0.25)


# ── _effective_n ───────────────────────────────────────────────────────────────

def test_effective_n_uniform_weights_equals_count():
    weights = [1.0, 1.0, 1.0, 1.0]
    assert calibrate._effective_n(weights) == pytest.approx(4.0)


def test_effective_n_empty_returns_zero():
    assert calibrate._effective_n([]) == 0.0


def test_effective_n_single_weight_equals_one():
    assert calibrate._effective_n([0.7]) == pytest.approx(1.0)


# ── _confidence ────────────────────────────────────────────────────────────────

def test_confidence_high_at_15():
    assert calibrate._confidence(15) == "high"


def test_confidence_medium_at_10():
    assert calibrate._confidence(10) == "medium"


def test_confidence_low_at_6():
    assert calibrate._confidence(6) == "low"


def test_confidence_none_below_min():
    assert calibrate._confidence(4) is None


# ── _normalize_tag ─────────────────────────────────────────────────────────────

def test_normalize_tag_adds_brackets():
    assert calibrate._normalize_tag("BE") == "[BE]"


def test_normalize_tag_preserves_existing_brackets():
    assert calibrate._normalize_tag("[BE]") == "[BE]"


def test_normalize_tag_fe_admin():
    assert calibrate._normalize_tag("FE-Admin") == "[FE-Admin]"


# ── _parse_records ──────────────────────────────────────────────────────────────

def test_parse_records_extracts_is_carry_over():
    line = _make_record("BE", "carry_over")
    records = calibrate._parse_records([line])
    assert records[0]["is_carry_over"] is True


def test_parse_records_completed_not_carry_over():
    line = _make_record("BE", "completed")
    records = calibrate._parse_records([line])
    assert records[0]["is_carry_over"] is False


def test_parse_records_normalizes_service_tag():
    line = _make_record("BE", "completed")
    records = calibrate._parse_records([line])
    assert records[0]["service_tag"] == "[BE]"


def test_parse_records_extracts_keywords_from_summary():
    line = _make_record("BE", "completed", summary="implement auth migration endpoint")
    records = calibrate._parse_records([line])
    kws = records[0]["keywords"]
    assert "auth" in kws
    assert "migration" in kws


def test_parse_records_skips_invalid_json():
    records = calibrate._parse_records(["not json", "", _make_record("BE", "completed")])
    assert len(records) == 1


def test_parse_records_computes_age_days():
    line = _make_record("BE", "completed", age_days=30)
    records = calibrate._parse_records([line])
    assert 29 <= records[0]["age_days"] <= 31


# ── _should_run ──────────────────────────────────────────────────────────────

def test_should_run_true_when_10_new_records():
    cal = {"last_calibrated_record_count": 5}
    assert calibrate._should_run(15, cal) is True


def test_should_run_false_when_fewer_than_10_new():
    cal = {"last_calibrated_record_count": 10,
           "generated_at": datetime.now(UTC).isoformat()}
    assert calibrate._should_run(14, cal) is False


def test_should_run_true_when_calibration_older_than_7_days():
    old_ts = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    cal = {"last_calibrated_record_count": 10, "generated_at": old_ts}
    assert calibrate._should_run(10, cal) is True


def test_should_run_true_when_no_generated_at():
    cal = {"last_calibrated_record_count": 10}
    assert calibrate._should_run(10, cal) is True


# ── _write_atomic ──────────────────────────────────────────────────────────────

def test_write_atomic_creates_file_with_correct_content(tmp_path):
    path = tmp_path / "cal.json"
    calibrate._write_atomic(path, {"key": "value"})
    data = json.loads(path.read_text())
    assert data["key"] == "value"


def test_write_atomic_file_permissions_are_600(tmp_path):
    path = tmp_path / "cal.json"
    calibrate._write_atomic(path, {"x": 1})
    mode = oct(path.stat().st_mode)[-3:]
    assert mode == "600"


def test_write_atomic_no_tmp_file_left_on_success(tmp_path):
    path = tmp_path / "cal.json"
    calibrate._write_atomic(path, {"x": 1})
    assert not (tmp_path / "cal.tmp").exists()


# ── run_calibration ────────────────────────────────────────────────────────────

def test_run_calibration_returns_none_when_outcomes_missing(tmp_path):
    result = calibrate.run_calibration(
        outcomes_path=tmp_path / "missing.jsonl",
        calibration_path=tmp_path / "cal.json",
    )
    assert result is None


def test_run_calibration_skips_when_threshold_not_met(tmp_path):
    records = [_make_record("BE", "completed") for _ in range(5)]
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    cal_path.write_text(json.dumps({
        "last_calibrated_record_count": 2,
        "generated_at": datetime.now(UTC).isoformat(),
    }))
    # 5 records, last_count=2, delta=3 < 10 → skip
    result = calibrate.run_calibration(outcomes_path=outcomes, calibration_path=cal_path)
    assert result is None


def test_run_calibration_force_bypasses_threshold(tmp_path):
    records = [_make_record("BE", "completed") for _ in range(3)]
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    # With 3 records all for BE, effective_n=3 → below min, excluded
    assert result is not None
    assert result["schema_version"] == 1


def test_run_calibration_writes_calibration_json(tmp_path):
    records = [_make_record("[BE]", "carry_over", age_days=i) for i in range(20)]
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    assert cal_path.exists()
    written = json.loads(cal_path.read_text())
    assert written["schema_version"] == 1
    assert "team_carry_over_baseline" in written


def test_run_calibration_team_baseline_derived_from_data(tmp_path):
    # 20 carry_over + 5 completed for [BE] → carry_over_rate ≈ 0.8
    records = (
        [_make_record("BE", "carry_over", age_days=i) for i in range(20)]
        + [_make_record("BE", "completed", age_days=i) for i in range(5)]
    )
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    # Team baseline should be derived from data, not hardcoded 0.20
    assert result["team_carry_over_baseline"] != pytest.approx(0.20, abs=0.01)


def test_run_calibration_fallback_baseline_when_fewer_than_15_records(tmp_path):
    records = [_make_record("BE", "carry_over") for _ in range(10)]
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    # 10 records total < 15 → fallback 0.20
    assert result["team_carry_over_baseline"] == pytest.approx(0.20)


def test_run_calibration_excluded_groups_below_min_n(tmp_path):
    # 3 records for Video → below _MIN_N=5 → excluded
    records = [_make_record("Video", "carry_over") for _ in range(3)]
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    assert "[Video]" in result["excluded_groups"]


def test_run_calibration_low_confidence_not_in_service_tags(tmp_path):
    # 6 records → effective_n ~6 → "low" confidence → written but not inject-eligible
    records = [_make_record("BE", "carry_over", age_days=i) for i in range(6)]
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    if "[BE]" in result.get("service_tags", {}):
        assert result["service_tags"]["[BE]"]["confidence"] == "low"


def test_run_calibration_keyword_risk_only_allowlisted(tmp_path, monkeypatch):
    # Summary with "auth" (allowlisted) and "xyzzy" (not allowlisted)
    records = [
        _make_record("BE", "carry_over", summary="fix auth integration issue"),
        _make_record("BE", "carry_over", summary="xyzzy injection attack"),
        _make_record("BE", "completed", summary="add auth endpoint"),
    ] * 6  # 18 records
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    # Patch allowlist to only contain "auth"
    monkeypatch.setattr(calibrate, "load_allowlist", lambda: {"auth"})
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    if "[BE]" in result.get("service_tags", {}):
        kw_risk = result["service_tags"]["[BE]"].get("keyword_risk", {})
        assert "xyzzy" not in kw_risk
        # "auth" may or may not appear depending on odds ratio threshold


def test_run_calibration_signal_thresholds_preserved_from_existing(tmp_path):
    records = [_make_record("BE", "carry_over", age_days=i) for i in range(20)]
    outcomes = _write_outcomes(tmp_path, records)
    cal_path = tmp_path / "cal.json"
    existing = {
        "signal_thresholds": {
            "velocity_drop_sigma": 3.0,  # custom value
            "carry_over_spike_pct": 0.50,
            "stagnant_days_default": 10,
            "stagnant_days_override": {"[FE-Web]": 5},
            "sp_mismatch_pct": 2.0,
            "sp_mismatch_grace_hours": 6,
        }
    }
    cal_path.write_text(json.dumps(existing))
    result = calibrate.run_calibration(
        outcomes_path=outcomes, calibration_path=cal_path, force=True
    )
    assert result["signal_thresholds"]["velocity_drop_sigma"] == 3.0
    assert result["signal_thresholds"]["stagnant_days_override"]["[FE-Web]"] == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/kobig/Codes/Personals/atlassian-pm
python3 -m pytest tests/scripts/test_calibrate.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'calibrate'` or similar.

- [ ] **Step 3: Implement calibrate.py**

Create `scripts/ai/calibrate.py`:

```python
#!/usr/bin/env python3
"""Calibration engine — builds calibration.json from story-outcomes.jsonl.

Self-gating: runs only when ≥10 new records OR >7 days since last calibration
OR --force flag.

Algorithm: decay-weighted carry_over_rate + weighted odds ratio keyword risk.

Usage:
    python3 scripts/ai/calibrate.py
    python3 scripts/ai/calibrate.py --force
    python3 scripts/ai/calibrate.py --prune
"""

import argparse
import fcntl
import json
import math
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts" / "ai"))

_DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)
_OUTCOMES_FILE = _DATA_DIR / "story-outcomes.jsonl"
_CALIBRATION_FILE = _DATA_DIR / "calibration.json"
_ALLOWLIST_FILE = Path(__file__).parent / "keyword_allowlist.json"

_MIN_N = 5
_TRIGGER_RECORDS = 10
_TRIGGER_DAYS = 7
_MAX_RECORDS = 200
_PRUNE_KEEP = 500
_SCHEMA_VERSION = 1
_HALF_LIFE_DAYS = 60
_ODDS_RATIO_THRESHOLD = 1.2
_MIN_RECORDS_FOR_DERIVED_BASELINE = 15
_FALLBACK_BASELINE = 0.20

_DEFAULT_THRESHOLDS = {
    "velocity_drop_sigma": 2.0,
    "carry_over_spike_pct": 0.40,
    "stagnant_days_default": 7,
    "stagnant_days_override": {},
    "sp_mismatch_pct": 1.5,
    "sp_mismatch_grace_hours": 4,
}

_STOP_WORDS = {"the", "and", "for", "with", "this", "that", "from", "into", "upon"}


def load_allowlist() -> set[str]:
    """Load keyword allowlist from JSON file. Returns empty set on error."""
    try:
        data = json.loads(_ALLOWLIST_FILE.read_text())
        return set(data) if isinstance(data, list) else set()
    except (json.JSONDecodeError, OSError):
        return set()


def load_calibration(path: Path = _CALIBRATION_FILE) -> dict:
    """Load existing calibration.json. Returns empty dict on missing/error."""
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _normalize_tag(tag: str) -> str:
    """Normalize service_tag to bracket form: 'BE' → '[BE]'."""
    tag = tag.strip()
    if tag.startswith("[") and tag.endswith("]"):
        return tag
    return f"[{tag}]"


def _extract_keywords(summary: str) -> list[str]:
    """Extract lowercase word tokens ≥4 chars from summary, deduped."""
    tokens = re.findall(r"[a-zA-Z]+", summary.lower())
    seen: set[str] = set()
    result = []
    for t in tokens:
        if len(t) >= 4 and t not in _STOP_WORDS and t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _weight(age_days: float) -> float:
    """Exponential decay weight — half-life 60 days."""
    return 0.5 ** (age_days / _HALF_LIFE_DAYS)


def _effective_n(weights: list[float]) -> float:
    """Kish effective sample size: (Σw)² / Σ(w²)."""
    if not weights:
        return 0.0
    sum_w = sum(weights)
    sum_w2 = sum(w * w for w in weights)
    if sum_w2 == 0:
        return 0.0
    return (sum_w ** 2) / sum_w2


def _confidence(eff_n: float) -> str | None:
    """Map effective_n to confidence tier. Returns None if below minimum."""
    if eff_n >= 15:
        return "high"
    if eff_n >= 8:
        return "medium"
    if eff_n >= _MIN_N:
        return "low"
    return None


def _parse_records(lines: list[str]) -> list[dict]:
    """Parse JSONL lines. Adds age_days, is_carry_over, normalized service_tag, keywords."""
    now = datetime.now(UTC)
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue

        ts_str = r.get("ts") or r.get("completed_at") or ""
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            age_days = max((now - ts).total_seconds() / 86400, 0.0)
        except (ValueError, AttributeError):
            age_days = 0.0

        tag = r.get("service_tag") or ""
        records.append({
            **r,
            "age_days": age_days,
            "is_carry_over": r.get("outcome") == "carry_over",
            "service_tag": _normalize_tag(tag) if tag else "",
            "keywords": _extract_keywords(str(r.get("summary") or "")),
        })
    return records


def _compute_keyword_risk(
    group_records: list[dict],
    group_weights: list[float],
    tag_sum_w: float,
    tag_carry_sum_w: float,
    allowlist: set[str],
) -> dict:
    """Weighted odds ratio with Laplace α=1 for allowlisted keywords."""
    alpha = 1.0
    # Collect per-keyword (is_carry_over, weight) pairs
    kw_entries: dict[str, list[tuple[bool, float]]] = {}
    for r, w in zip(group_records, group_weights):
        for kw in r["keywords"]:
            if kw not in allowlist:
                continue
            kw_entries.setdefault(kw, []).append((r["is_carry_over"], w))

    result = {}
    for kw, entries in kw_entries.items():
        a = sum(w for co, w in entries if co) + alpha
        b = sum(w for co, w in entries if not co) + alpha
        kw_carry_sum = a - alpha
        kw_not_carry_sum = b - alpha
        c = max(tag_carry_sum_w - kw_carry_sum, 0.0) + alpha
        d = max((tag_sum_w - tag_carry_sum_w) - kw_not_carry_sum, 0.0) + alpha

        if b * c == 0:
            continue
        odds_ratio = (a * d) / (b * c)
        if odds_ratio <= _ODDS_RATIO_THRESHOLD:
            continue

        kw_weights = [w for _, w in entries]
        kw_eff_n = _effective_n(kw_weights)
        kw_conf = _confidence(kw_eff_n) or "low"
        result[kw] = {"odds_ratio": round(odds_ratio, 2), "confidence": kw_conf}
    return result


def _should_run(current_count: int, calibration: dict) -> bool:
    """Return True if calibration should run."""
    last_count = calibration.get("last_calibrated_record_count", 0)
    if (current_count - last_count) >= _TRIGGER_RECORDS:
        return True
    gen_at = calibration.get("generated_at", "")
    if not gen_at:
        return True
    try:
        ts = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if (datetime.now(UTC) - ts).total_seconds() / 86400 > _TRIGGER_DAYS:
            return True
    except (ValueError, AttributeError):
        return True
    return False


def _write_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically with 0o600 permissions."""
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", opener=lambda p, f: os.open(p, f, 0o600)) as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _prune_outcomes(path: Path, keep: int = _PRUNE_KEEP) -> None:
    """Prune story-outcomes.jsonl to last `keep` lines with fcntl lock."""
    if not path.exists():
        return
    tmp = Path(str(path) + ".tmp")
    try:
        with open(path, "r+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                lines = fh.readlines()
                if len(lines) <= keep:
                    return
                with open(tmp, "w", opener=lambda p, f: os.open(p, f, 0o600)) as tf:
                    tf.writelines(lines[-keep:])
                os.replace(tmp, path)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
    except OSError:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def run_calibration(
    outcomes_path: Path = _OUTCOMES_FILE,
    calibration_path: Path = _CALIBRATION_FILE,
    force: bool = False,
) -> dict | None:
    """Run calibration. Returns result dict or None if skipped/no data."""
    if not outcomes_path.exists():
        return None

    lines = outcomes_path.read_text().splitlines()
    current_count = sum(1 for l in lines if l.strip())

    existing_cal = load_calibration(calibration_path)
    if not force and not _should_run(current_count, existing_cal):
        return None

    records = _parse_records(lines[-_MAX_RECORDS:])
    if not records:
        return None

    allowlist = load_allowlist()

    # Group by service_tag
    groups: dict[str, list[dict]] = {}
    for r in records:
        tag = r["service_tag"]
        if tag:
            groups.setdefault(tag, []).append(r)

    service_tags_out: dict = {}
    excluded_groups: dict = {}

    for tag, grp in groups.items():
        weights = [_weight(r["age_days"]) for r in grp]
        sum_w = sum(weights)
        if sum_w == 0:
            continue

        carry_sum_w = sum(w for r, w in zip(grp, weights) if r["is_carry_over"])
        carry_over_rate = carry_sum_w / sum_w
        decay_weight_mean = sum_w / len(weights)
        eff_n = _effective_n(weights)
        conf = _confidence(eff_n)

        if conf is None:
            excluded_groups[tag] = {"record_count": len(grp), "reason": "below_min_n"}
            continue

        keyword_risk = _compute_keyword_risk(grp, weights, sum_w, carry_sum_w, allowlist)

        service_tags_out[tag] = {
            "carry_over_rate": round(carry_over_rate, 4),
            "n": len(grp),
            "confidence": conf,
            "decay_weight": round(decay_weight_mean, 4),
            "keyword_risk": keyword_risk,
            "keyword_method": "weighted_odds_ratio_laplace_alpha1",
        }

    # Team baseline
    inject_eligible = [
        (v["carry_over_rate"], _effective_n([_weight(r["age_days"]) for r in groups[t]]))
        for t, v in service_tags_out.items()
        if v.get("confidence") in ("high", "medium")
    ]

    if current_count >= _MIN_RECORDS_FOR_DERIVED_BASELINE and inject_eligible:
        total_eff_n = sum(en for _, en in inject_eligible)
        team_baseline = (
            sum(rate * en for rate, en in inject_eligible) / total_eff_n
            if total_eff_n > 0
            else _FALLBACK_BASELINE
        )
    else:
        team_baseline = _FALLBACK_BASELINE
        import logging
        logging.getLogger(__name__).warning(
            "Calibration: using fallback baseline %.2f (records=%d < %d)",
            _FALLBACK_BASELINE, current_count, _MIN_RECORDS_FOR_DERIVED_BASELINE,
        )

    signal_thresholds = existing_cal.get("signal_thresholds", _DEFAULT_THRESHOLDS.copy())

    result: dict = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "record_count": current_count,
        "last_calibrated_record_count": current_count,
        "team_carry_over_baseline": round(team_baseline, 4),
        "excluded_groups": excluded_groups,
        "service_tags": service_tags_out,
        "signal_thresholds": signal_thresholds,
        "calibration_model": "haiku",
    }

    # Optional Haiku note synthesis (failures are non-fatal)
    inject_tags = {t: v for t, v in service_tags_out.items()
                   if v.get("confidence") in ("high", "medium")}
    if inject_tags:
        try:
            from claude_runner import run_claude
            from prompts_calibrate import build_calibrate_prompt

            prompt = build_calibrate_prompt(inject_tags)
            response = run_claude(prompt, model="haiku", timeout=30)
            if response:
                try:
                    notes = json.loads(response)
                    if isinstance(notes, dict):
                        for tag, note in notes.items():
                            if tag in service_tags_out and isinstance(note, str):
                                service_tags_out[tag]["note"] = note[:200]
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass  # Notes are optional — never fail calibration for this

    _write_atomic(calibration_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run calibration on story-outcomes.jsonl")
    parser.add_argument("--force", action="store_true", help="Skip self-gating check")
    parser.add_argument("--prune", action="store_true", help="Prune outcomes to last 500 records")
    parser.add_argument("--dry-run", action="store_true", help="Print result, don't write")
    args = parser.parse_args()

    if args.prune:
        _prune_outcomes(_OUTCOMES_FILE)
        print("Pruned story-outcomes.jsonl to last 500 records", file=sys.stderr)

    result = run_calibration(force=args.force)
    if result is None:
        print("Calibration skipped (threshold not met or no data)", file=sys.stderr)
        return

    n_tags = len(result.get("service_tags", {}))
    baseline = result.get("team_carry_over_baseline", "n/a")
    print(f"Calibration complete: {n_tags} service tags, baseline={baseline}", file=sys.stderr)
    if args.dry_run:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/scripts/test_calibrate.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ai/calibrate.py tests/scripts/test_calibrate.py
git commit -m "feat(intelligence/g1): calibration engine with decay-weighted odds ratio"
```

---

## Task 3: velocity_adjust.py — calibration integration

**Files:**
- Modify: `scripts/ai/velocity_adjust.py`
- Modify: `tests/scripts/test_velocity_adjust.py` (add calibration tests)

- [ ] **Step 1: Add failing tests to test_velocity_adjust.py**

Append to end of `tests/scripts/test_velocity_adjust.py`:

```python
# ── compute_adjustment — calibration path ─────────────────────────────────────

def test_compute_adjustment_cal_adj_adds_to_trend_when_above_baseline():
    # carry_over_rate=0.40, baseline=0.20 → raw_cal=(0.40-0.20)*50=10 → cal_adj=10
    velocity = {"rolling_average": 40, "trend_pct": -8, "std_dev": 4}
    calibration = {
        "team_carry_over_baseline": 0.20,
        "service_tags": {
            "[BE]": {"carry_over_rate": 0.40, "n": 20, "confidence": "high"}
        }
    }
    adj = compute_adjustment(velocity, calibration=calibration, service_tag="[BE]")
    # trend_adj = -8*0.5 = -4, cal_adj = +10 → but cancellation floor applies
    # trend_adj < 0 and cal_adj > 0 → cap cal_adj at abs(-4)*0.5 = 2
    # total = -4 + 2 = -2
    assert adj["adjustment_pct"] == pytest.approx(-2.0)


def test_compute_adjustment_cal_adj_clamped_at_10():
    # carry_over_rate=0.50, baseline=0.10 → raw=(0.50-0.10)*50=20 → clamped to 10
    velocity = {"rolling_average": 40, "trend_pct": 0, "std_dev": 4}
    calibration = {
        "team_carry_over_baseline": 0.10,
        "service_tags": {
            "[BE]": {"carry_over_rate": 0.50, "n": 20, "confidence": "high"}
        }
    }
    adj = compute_adjustment(velocity, calibration=calibration, service_tag="[BE]")
    assert adj["adjustment_pct"] == pytest.approx(0.0)  # no trend_adj, no negative cal_adj → 0


def test_compute_adjustment_cal_adj_negative_when_below_baseline():
    # carry_over_rate=0.10, baseline=0.30 → raw=(0.10-0.30)*50=-10 → cal_adj=-10
    velocity = {"rolling_average": 40, "trend_pct": 0, "std_dev": 4}
    calibration = {
        "team_carry_over_baseline": 0.30,
        "service_tags": {
            "[BE]": {"carry_over_rate": 0.10, "n": 20, "confidence": "high"}
        }
    }
    adj = compute_adjustment(velocity, calibration=calibration, service_tag="[BE]")
    # trend_adj=0, cal_adj=-10, total=-10 → clamped to -10 (within ±20)
    assert adj["adjustment_pct"] == pytest.approx(-10.0)


def test_compute_adjustment_cal_adj_zero_for_low_confidence():
    velocity = {"rolling_average": 40, "trend_pct": 0, "std_dev": 4}
    calibration = {
        "team_carry_over_baseline": 0.20,
        "service_tags": {
            "[BE]": {"carry_over_rate": 0.50, "n": 6, "confidence": "low"}
        }
    }
    adj = compute_adjustment(velocity, calibration=calibration, service_tag="[BE]")
    assert adj["adjustment_pct"] == 0.0


def test_compute_adjustment_cal_adj_zero_when_tag_not_in_calibration():
    velocity = {"rolling_average": 40, "trend_pct": -8, "std_dev": 4}
    calibration = {
        "team_carry_over_baseline": 0.20,
        "service_tags": {}
    }
    adj = compute_adjustment(velocity, calibration=calibration, service_tag="[BE]")
    # Only trend_adj applies: max(-8*0.5, -15) = -4
    assert adj["adjustment_pct"] == pytest.approx(-4.0)


def test_compute_adjustment_absent_calibration_passthrough():
    velocity = {"rolling_average": 40, "trend_pct": -8, "std_dev": 4}
    adj = compute_adjustment(velocity, calibration=None, service_tag="[BE]")
    assert adj["adjustment_pct"] == pytest.approx(-4.0)


def test_compute_adjustment_combined_cap_at_minus_20():
    # trend_adj=-15 (cap), cal_adj=-10 → total=-25 → clamped to -20
    velocity = {"rolling_average": 40, "trend_pct": -40, "std_dev": 4}
    calibration = {
        "team_carry_over_baseline": 0.30,
        "service_tags": {
            "[BE]": {"carry_over_rate": 0.10, "n": 20, "confidence": "high"}
        }
    }
    adj = compute_adjustment(velocity, calibration=calibration, service_tag="[BE]")
    assert adj["adjustment_pct"] == pytest.approx(-20.0)
```

- [ ] **Step 2: Run tests to verify new tests fail**

```bash
python3 -m pytest tests/scripts/test_velocity_adjust.py::test_compute_adjustment_cal_adj_adds_to_trend_when_above_baseline -v
```

Expected: `FAILED` — `compute_adjustment() got unexpected keyword argument 'calibration'`.

- [ ] **Step 3: Modify velocity_adjust.py**

Replace `compute_adjustment` and add `load_calibration_data`:

```python
def load_calibration_data(data_dir: Path | None = None) -> dict | None:
    """Load calibration.json from CLAUDE_PLUGIN_DATA. Returns None on error."""
    import os
    if data_dir is None:
        data_dir = Path(
            os.environ.get(
                "CLAUDE_PLUGIN_DATA",
                str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
            )
        )
    cal_path = data_dir / "calibration.json"
    try:
        return json.loads(cal_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def compute_adjustment(
    velocity: dict,
    calibration: dict | None = None,
    service_tag: str | None = None,
) -> dict:
    """Compute SP adjustment factor from velocity data + optional calibration signal."""
    story_points = velocity.get("story_points", {})
    avg = (
        story_points.get("avg_velocity")
        or velocity.get("rolling_average", 0)
        or 0
    )
    trend_pct = velocity.get("trend_pct", 0)
    std_dev = (
        story_points.get("std_dev")
        or velocity.get("std_dev", 0)
        or 0
    )

    # Trend adjustment (unchanged from original)
    trend_adj = 0.0
    note = ""
    if trend_pct < -5:
        trend_adj = max(trend_pct * 0.5, -15)
        note = f"team velocity declining {abs(trend_pct):.0f}%"
    elif trend_pct > 5:
        note = f"team velocity improving {trend_pct:.0f}%"

    # Calibration adjustment
    cal_adj = 0.0
    if calibration and service_tag:
        tag_data = calibration.get("service_tags", {}).get(service_tag, {})
        if tag_data.get("confidence") in ("high", "medium"):
            rate = tag_data["carry_over_rate"]
            baseline = calibration.get("team_carry_over_baseline", 0.20)
            raw_cal = (rate - baseline) * 50
            cal_adj = max(min(raw_cal, 10.0), -10.0)  # symmetric clamp ±10

    # Signal cancellation floor: if trend improving carry-over risk, cap cal_adj
    if trend_adj < 0 and cal_adj > 0:
        cal_adj = min(cal_adj, abs(trend_adj) * 0.5)

    adjustment_pct = max(min(trend_adj + cal_adj, 20.0), -20.0)
    high_variance = std_dev > avg * 0.2 if avg > 0 else False

    return {
        "rolling_average": avg,
        "trend_pct": trend_pct,
        "std_dev": std_dev,
        "adjustment_pct": adjustment_pct,
        "note": note,
        "high_variance": high_variance,
    }
```

Also update `main()` in velocity_adjust.py to load calibration:

```python
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print velocity context for SP estimation prompts"
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Path to project-config-team-detail.json (auto-discovered if omitted)",
    )
    parser.add_argument(
        "--service-tag", type=str, default=None,
        help="Service tag for calibration lookup (e.g. [BE])",
    )
    args = parser.parse_args()

    velocity = load_velocity(args.config)
    if velocity is None:
        sys.exit(0)

    calibration = load_calibration_data()
    adj = compute_adjustment(velocity, calibration=calibration, service_tag=args.service_tag)
    print(format_context(adj))
```

- [ ] **Step 4: Run all velocity_adjust tests**

```bash
python3 -m pytest tests/scripts/test_velocity_adjust.py -v
```

Expected: All tests PASS (including the original ones — `compute_adjustment` is backward-compatible since `calibration` defaults to None).

- [ ] **Step 5: Commit**

```bash
git add scripts/ai/velocity_adjust.py tests/scripts/test_velocity_adjust.py
git commit -m "feat(intelligence/g1): velocity_adjust reads calibration signal with cancellation floor"
```

---

## Task 4: Proactive analyzer — TDD

**Files:**
- Create: `tests/monitor/__init__.py`
- Create: `tests/monitor/test_intelligence_analyzer.py`
- Create: `monitor/handlers/intelligence_analyzer.py`

- [ ] **Step 1: Create test package and write failing tests**

```bash
touch tests/monitor/__init__.py
```

Create `tests/monitor/test_intelligence_analyzer.py`:

```python
"""Tests for monitor/handlers/intelligence_analyzer.py."""
import json
import os
import sys
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from monitor.handlers import intelligence_analyzer as ia


def _now_iso(delta_days=0):
    return (datetime.now(UTC) + timedelta(days=delta_days)).isoformat()


def _make_snapshot(keys_statuses: dict) -> dict:
    """Build minimal snapshot: {key: {status, sprint_end_date, status_since, issuetype, sp, parent}}."""
    snap = {}
    for key, status in keys_statuses.items():
        snap[key] = {
            "summary": f"Issue {key}",
            "status": status,
            "assignee": "",
            "priority": "Medium",
            "sprint_end_date": None,
            "status_since": _now_iso(-1),
            "issuetype": "Story",
            "sp": 3,
            "parent": None,
        }
    return snap


_DEFAULT_THRESHOLDS = {
    "velocity_drop_sigma": 2.0,
    "carry_over_spike_pct": 0.40,
    "stagnant_days_default": 7,
    "stagnant_days_override": {},
    "sp_mismatch_pct": 1.5,
    "sp_mismatch_grace_hours": 4,
}

_DEFAULT_CALIBRATION = {
    "schema_version": 1,
    "signal_thresholds": _DEFAULT_THRESHOLDS,
    "service_tags": {},
    "team_carry_over_baseline": 0.20,
}

_BOARD_CONFIG = {
    "columns": {
        "Backlog":        {"wip_max": None, "statuses": ["Backlog", "To Do"]},
        "In Progress":    {"wip_max": 3,    "statuses": ["In Progress"]},
        "In QA":          {"wip_max": 2,    "statuses": ["In QA"]},
        "Done":           {"wip_max": None, "statuses": ["Done"]},
    }
}


# ── _weight / _effective_n helpers (no state) ─────────────────────────────────

def test_detect_wip_breach_fires_when_column_over_limit():
    snapshot = _make_snapshot({
        "{{PROJECT_KEY}}-1": "In Progress", "{{PROJECT_KEY}}-2": "In Progress",
        "{{PROJECT_KEY}}-3": "In Progress", "{{PROJECT_KEY}}-4": "In Progress",  # 4 > max 3
    })
    # tracking state: wip_breach already tracked for 2 cycles
    tracking = {"In Progress": {"count": 2, "last_seen": _now_iso()}}
    signals = ia._detect_wip_breach(snapshot, _BOARD_CONFIG, tracking, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "wip_breach" for s in signals)


def test_detect_wip_breach_does_not_fire_before_3_consecutive_cycles():
    snapshot = _make_snapshot({
        "{{PROJECT_KEY}}-1": "In Progress", "{{PROJECT_KEY}}-2": "In Progress",
        "{{PROJECT_KEY}}-3": "In Progress", "{{PROJECT_KEY}}-4": "In Progress",
    })
    # Only 1 cycle tracked so far
    tracking = {"In Progress": {"count": 1, "last_seen": _now_iso()}}
    signals = ia._detect_wip_breach(snapshot, _BOARD_CONFIG, tracking, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "wip_breach" for s in signals)


def test_detect_wip_breach_no_signal_when_within_limit():
    snapshot = _make_snapshot({
        "{{PROJECT_KEY}}-1": "In Progress", "{{PROJECT_KEY}}-2": "In Progress",  # 2 ≤ max 3
    })
    tracking = {"In Progress": {"count": 5, "last_seen": _now_iso()}}
    signals = ia._detect_wip_breach(snapshot, _BOARD_CONFIG, tracking, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "wip_breach" for s in signals)


def test_detect_stagnant_issues_fires_when_status_since_too_old():
    snap = _make_snapshot({"{{PROJECT_KEY}}-1": "In Progress"})
    snap["{{PROJECT_KEY}}-1"]["status_since"] = _now_iso(-8)  # 8 days ago, threshold=7
    signals = ia._detect_stagnant_issues(snap, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "stagnant_issue" and s["affected_keys"] == ["{{PROJECT_KEY}}-1"]
               for s in signals)


def test_detect_stagnant_issues_no_signal_within_threshold():
    snap = _make_snapshot({"{{PROJECT_KEY}}-1": "In Progress"})
    snap["{{PROJECT_KEY}}-1"]["status_since"] = _now_iso(-5)  # 5 days ago < threshold=7
    signals = ia._detect_stagnant_issues(snap, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "stagnant_issue" for s in signals)


def test_detect_stagnant_issues_uses_per_tag_override(tmp_path):
    thresholds = {**_DEFAULT_THRESHOLDS, "stagnant_days_override": {"[FE-Web]": 3}}
    snap = _make_snapshot({"{{PROJECT_KEY}}-1": "In Progress"})
    snap["{{PROJECT_KEY}}-1"]["status_since"] = _now_iso(-4)  # 4 > 3 (override)
    snap["{{PROJECT_KEY}}-1"]["service_tag"] = "[FE-Web]"
    signals = ia._detect_stagnant_issues(snap, thresholds)
    assert any(s["signal"] == "stagnant_issue" for s in signals)


def test_detect_stagnant_issues_not_triggered_for_non_in_progress():
    snap = _make_snapshot({"{{PROJECT_KEY}}-1": "In QA"})
    snap["{{PROJECT_KEY}}-1"]["status_since"] = _now_iso(-10)
    signals = ia._detect_stagnant_issues(snap, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "stagnant_issue" for s in signals)


def test_detect_carry_over_spike_fires_above_threshold(tmp_path):
    outcomes_path = tmp_path / "story-outcomes.jsonl"
    sprint_id = "42"
    # 3 carry_over, 2 completed in sprint 42 → rate=0.6 > threshold=0.4
    records = [
        {"sprint_id": sprint_id, "outcome": "carry_over", "service_tag": "BE",
         "issue_key": f"TP-{i}", "ts": _now_iso(-2)} for i in range(3)
    ] + [
        {"sprint_id": sprint_id, "outcome": "completed", "service_tag": "BE",
         "issue_key": f"TP-{i+10}", "ts": _now_iso(-2)} for i in range(2)
    ]
    outcomes_path.write_text("\n".join(json.dumps(r) for r in records))
    signals = ia._detect_carry_over_spike(outcomes_path, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "carry_over_spike" for s in signals)


def test_detect_carry_over_spike_no_signal_below_threshold(tmp_path):
    outcomes_path = tmp_path / "story-outcomes.jsonl"
    sprint_id = "42"
    # 1 carry_over, 4 completed → rate=0.2 < threshold=0.4
    records = [
        {"sprint_id": sprint_id, "outcome": "carry_over", "service_tag": "BE",
         "issue_key": "{{PROJECT_KEY}}-1", "ts": _now_iso(-2)},
    ] + [
        {"sprint_id": sprint_id, "outcome": "completed", "service_tag": "BE",
         "issue_key": f"TP-{i+2}", "ts": _now_iso(-2)} for i in range(4)
    ]
    outcomes_path.write_text("\n".join(json.dumps(r) for r in records))
    signals = ia._detect_carry_over_spike(outcomes_path, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "carry_over_spike" for s in signals)


def test_detect_carry_over_spike_requires_min_5_items(tmp_path):
    outcomes_path = tmp_path / "story-outcomes.jsonl"
    # Only 4 items, 3 carry_over → rate=0.75 but below guard (< 5 items)
    records = [
        {"sprint_id": "42", "outcome": "carry_over", "service_tag": "BE",
         "issue_key": f"TP-{i}", "ts": _now_iso(-2)} for i in range(3)
    ] + [
        {"sprint_id": "42", "outcome": "completed", "service_tag": "BE",
         "issue_key": "{{PROJECT_KEY}}-99", "ts": _now_iso(-2)}
    ]
    outcomes_path.write_text("\n".join(json.dumps(r) for r in records))
    signals = ia._detect_carry_over_spike(outcomes_path, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "carry_over_spike" for s in signals)


def test_detect_sp_mismatch_fires_when_subtasks_exceed_parent(tmp_path):
    # Parent {{PROJECT_KEY}}-10: sp=3, In Progress since 5h ago (> grace 4h)
    # Subtasks: {{PROJECT_KEY}}-11 sp=2, {{PROJECT_KEY}}-12 sp=3 → sum=5 > 1.5*3=4.5
    snap = {
        "{{PROJECT_KEY}}-10": {
            "summary": "Parent story", "status": "In Progress",
            "issuetype": "Story", "sp": 3, "parent": None,
            "status_since": _now_iso(-5 / 24),  # 5 hours ago
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
        "{{PROJECT_KEY}}-11": {
            "summary": "Subtask 1", "status": "In Progress",
            "issuetype": "Sub-task", "sp": 2, "parent": "{{PROJECT_KEY}}-10",
            "status_since": _now_iso(-1),
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
        "{{PROJECT_KEY}}-12": {
            "summary": "Subtask 2", "status": "To Do",
            "issuetype": "Sub-task", "sp": 3, "parent": "{{PROJECT_KEY}}-10",
            "status_since": _now_iso(-1),
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
    }
    signals = ia._detect_sp_mismatch(snap, _DEFAULT_THRESHOLDS)
    assert any(s["signal"] == "sp_mismatch" and "{{PROJECT_KEY}}-10" in s["affected_keys"]
               for s in signals)


def test_detect_sp_mismatch_no_signal_within_grace_period():
    # Parent transitioned to In Progress 2 hours ago (< grace 4h) → skip
    snap = {
        "{{PROJECT_KEY}}-10": {
            "summary": "Parent", "status": "In Progress",
            "issuetype": "Story", "sp": 3, "parent": None,
            "status_since": _now_iso(-2 / 24),  # 2 hours ago
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
        "{{PROJECT_KEY}}-11": {
            "summary": "Sub", "status": "To Do",
            "issuetype": "Sub-task", "sp": 10, "parent": "{{PROJECT_KEY}}-10",
            "status_since": _now_iso(-1),
            "assignee": "", "priority": "Medium", "sprint_end_date": None,
        },
    }
    signals = ia._detect_sp_mismatch(snap, _DEFAULT_THRESHOLDS)
    assert not any(s["signal"] == "sp_mismatch" for s in signals)


def test_evict_removes_expired_signals():
    now = datetime.now(UTC)
    signals = [
        {
            "signal": "stagnant_issue", "severity": "warning",
            "generated_at": (now - timedelta(hours=25)).isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),  # expired
            "affected_keys": ["{{PROJECT_KEY}}-1"],
        },
        {
            "signal": "wip_breach", "severity": "warning",
            "generated_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=23)).isoformat(),  # active
            "affected_keys": [],
        },
    ]
    result = ia._evict(signals)
    assert len(result) == 1
    assert result[0]["signal"] == "wip_breach"


def test_evict_caps_at_10_signals():
    now = datetime.now(UTC)
    signals = [
        {
            "signal": "stagnant_issue", "severity": "warning",
            "generated_at": (now - timedelta(hours=i)).isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "affected_keys": [f"TP-{i}"],
        }
        for i in range(15)
    ]
    result = ia._evict(signals)
    assert len(result) == 10


def test_analyze_writes_insights_json(tmp_path):
    outcomes = tmp_path / "story-outcomes.jsonl"
    insights = tmp_path / "insights.json"
    outcomes.write_text("")  # empty
    snap = _make_snapshot({"{{PROJECT_KEY}}-1": "In Progress"})
    snap["{{PROJECT_KEY}}-1"]["status_since"] = _now_iso(-8)

    ia.analyze(
        diff=[],
        new_snapshot=snap,
        old_snapshot={},
        calibration=_DEFAULT_CALIBRATION,
        board_config=_BOARD_CONFIG,
        velocity=None,
        outcomes_path=outcomes,
        insights_path=insights,
    )
    assert insights.exists()
    data = json.loads(insights.read_text())
    assert isinstance(data.get("signals"), list)


def test_analyze_stop_event_prevents_write(tmp_path):
    outcomes = tmp_path / "story-outcomes.jsonl"
    insights = tmp_path / "insights.json"
    outcomes.write_text("")
    stop = threading.Event()
    stop.set()  # already stopped

    ia.analyze(
        diff=[], new_snapshot={}, old_snapshot={},
        calibration=_DEFAULT_CALIBRATION,
        board_config=_BOARD_CONFIG, velocity=None,
        outcomes_path=outcomes, insights_path=insights,
        stop_event=stop,
    )
    assert not insights.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/monitor/test_intelligence_analyzer.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or import error.

- [ ] **Step 3: Implement intelligence_analyzer.py**

Create `monitor/handlers/intelligence_analyzer.py`:

```python
#!/usr/bin/env python3
"""Proactive board intelligence analyzer — pure Python, zero LLM calls.

Detects 5 signals from board snapshot + outcomes history. All thresholds are
read from calibration.json["signal_thresholds"] at runtime. Writes insights.json
atomically. Called from board_monitor.py in a daemon thread after snapshot save.
"""

import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)
_INSIGHTS_FILE = _DATA_DIR / "insights.json"
_OUTCOMES_FILE = _DATA_DIR / "story-outcomes.jsonl"
_MAX_ACTIVE_SIGNALS = 10

_TTL_HOURS = {
    "velocity_drop": 72,
    "carry_over_spike": 72,
    "wip_breach": 24,
    "stagnant_issue": 24,
    "sp_mismatch": 24,
}

_DEFAULT_THRESHOLDS = {
    "velocity_drop_sigma": 2.0,
    "carry_over_spike_pct": 0.40,
    "stagnant_days_default": 7,
    "stagnant_days_override": {},
    "sp_mismatch_pct": 1.5,
    "sp_mismatch_grace_hours": 4,
}


# ── File helpers ──────────────────────────────────────────────────────────────

def _load_insights(path: Path) -> dict:
    """Load insights.json → {signals: [], wip_breach_tracking: {}}."""
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return {"signals": [], "wip_breach_tracking": {}}
        data.setdefault("signals", [])
        data.setdefault("wip_breach_tracking", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"signals": [], "wip_breach_tracking": {}}


def _write_insights(path: Path, data: dict) -> None:
    """Write insights.json atomically with 0o600 permissions."""
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", opener=lambda p, f: os.open(p, f, 0o600)) as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _evict(signals: list[dict]) -> list[dict]:
    """Remove expired entries; cap at _MAX_ACTIVE_SIGNALS (oldest first)."""
    now = datetime.now(UTC)
    active = []
    for s in signals:
        try:
            exp = datetime.fromisoformat(s["expires_at"].replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if exp > now:
                active.append(s)
        except (KeyError, ValueError):
            active.append(s)  # keep if no expiry info
    # If still over cap, evict oldest by generated_at
    if len(active) > _MAX_ACTIVE_SIGNALS:
        active.sort(key=lambda s: s.get("generated_at", ""))
        active = active[-_MAX_ACTIVE_SIGNALS:]
    return active


def _is_dedup(signal_type: str, dedup_key: tuple, existing: list[dict]) -> bool:
    """Return True if a non-expired signal with same dedup_key already exists."""
    now = datetime.now(UTC)
    for s in existing:
        if s.get("signal") != signal_type:
            continue
        exp_str = s.get("expires_at", "")
        try:
            exp = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if exp <= now:
                continue
        except ValueError:
            pass
        if tuple(s.get("_dedup_key", [])) == dedup_key:
            return True
    return False


def _make_signal(
    signal: str,
    severity: str,
    dedup_key: tuple,
    metric_value: float,
    baseline_value: float,
    affected_keys: list[str],
    **extra: Any,
) -> dict:
    now = datetime.now(UTC)
    ttl_h = _TTL_HOURS.get(signal, 24)
    return {
        "signal": signal,
        "severity": severity,
        "metric_value": round(metric_value, 4),
        "baseline_value": round(baseline_value, 4),
        "delta_pct": round((metric_value - baseline_value) / max(baseline_value, 0.001) * 100),
        "affected_keys": affected_keys,
        "generated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=ttl_h)).isoformat(),
        "source": "ml-derived",
        "_dedup_key": list(dedup_key),
        **extra,
    }


# ── Signal detectors ──────────────────────────────────────────────────────────

def _detect_velocity_drop(
    velocity: dict | None,
    thresholds: dict,
    existing: list[dict],
) -> list[dict]:
    """Signal: recent velocity < rolling_mean - sigma * std_dev."""
    if not velocity:
        return []
    history = velocity.get("sprint_history") or velocity.get("story_points", {}).get("history", [])
    if len(history) < 3:
        return []
    sp_values = [float(e.get("completed_sp", 0)) for e in history if e.get("completed_sp") is not None]
    if len(sp_values) < 3:
        return []

    rolling = velocity.get("rolling_average") or (
        velocity.get("story_points", {}).get("avg_velocity")
    )
    std_dev = velocity.get("std_dev") or velocity.get("story_points", {}).get("std_dev")

    if rolling is None or std_dev is None or std_dev == 0:
        return []

    latest_sp = sp_values[-1]
    sigma = thresholds.get("velocity_drop_sigma", 2.0)
    threshold_value = float(rolling) - sigma * float(std_dev)

    if latest_sp >= threshold_value:
        return []

    sprint_id = history[-1].get("sprint_id") if history else "unknown"
    service_tag = "[all]"
    dedup_key = ("velocity_drop", service_tag, str(sprint_id))
    if _is_dedup("velocity_drop", dedup_key, existing):
        return []

    return [_make_signal(
        "velocity_drop", "warning", dedup_key,
        metric_value=latest_sp, baseline_value=float(rolling),
        affected_keys=[],
        service_tag=service_tag,
        sprint_id=sprint_id,
    )]


def _detect_carry_over_spike(
    outcomes_path: Path,
    thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: most recent sprint carry_over_rate > threshold."""
    if existing is None:
        existing = []
    if not outcomes_path.exists():
        return []

    records: list[dict] = []
    try:
        for line in outcomes_path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        return []

    if not records:
        return []

    # Find most recent sprint
    latest_sprint_id = records[-1].get("sprint_id")
    if latest_sprint_id is None:
        return []

    sprint_records = [r for r in records if r.get("sprint_id") == latest_sprint_id]
    if len(sprint_records) < 5:  # guard
        return []

    # Group by service_tag
    by_tag: dict[str, list[dict]] = {}
    for r in sprint_records:
        tag = r.get("service_tag") or "[all]"
        if not tag.startswith("["):
            tag = f"[{tag}]"
        by_tag.setdefault(tag, []).append(r)

    signals = []
    threshold_pct = thresholds.get("carry_over_spike_pct", 0.40)

    for tag, recs in by_tag.items():
        if len(recs) < 5:
            continue
        carry_over_count = sum(1 for r in recs if r.get("outcome") == "carry_over")
        rate = carry_over_count / len(recs)
        if rate <= threshold_pct:
            continue

        dedup_key = ("carry_over_spike", tag, str(latest_sprint_id))
        if _is_dedup("carry_over_spike", dedup_key, existing):
            continue

        affected = [r["issue_key"] for r in recs if r.get("outcome") == "carry_over" and r.get("issue_key")]
        signals.append(_make_signal(
            "carry_over_spike", "warning", dedup_key,
            metric_value=rate, baseline_value=threshold_pct,
            affected_keys=affected[:10],
            service_tag=tag,
            sprint_id=latest_sprint_id,
        ))

    return signals


def _detect_wip_breach(
    snapshot: dict,
    board_config: dict,
    tracking: dict,
    thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: WIP-limited column exceeds limit for >2 consecutive poll cycles."""
    if existing is None:
        existing = []
    columns = board_config.get("columns", {})
    signals = []

    for col_name, col_cfg in columns.items():
        wip_max = col_cfg.get("wip_max")
        if wip_max is None:
            continue
        statuses = col_cfg.get("statuses", [col_name])
        count = sum(
            1 for v in snapshot.values()
            if v.get("status") in statuses
        )
        if count > wip_max:
            entry = tracking.setdefault(col_name, {"count": 0, "last_seen": ""})
            entry["count"] += 1
            entry["last_seen"] = datetime.now(UTC).isoformat()

            if entry["count"] >= 3:
                dedup_key = ("wip_breach", col_name)
                if not _is_dedup("wip_breach", dedup_key, existing):
                    affected = [
                        k for k, v in snapshot.items()
                        if v.get("status") in statuses
                    ]
                    signals.append(_make_signal(
                        "wip_breach", "warning", dedup_key,
                        metric_value=float(count), baseline_value=float(wip_max),
                        affected_keys=affected[:10],
                        column=col_name,
                    ))
        else:
            # Reset tracking on recovery
            tracking.pop(col_name, None)

    return signals


def _detect_stagnant_issues(
    snapshot: dict,
    thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: issue In Progress > stagnant_days without status change."""
    if existing is None:
        existing = []
    stagnant_days = thresholds.get("stagnant_days_default", 7)
    overrides = thresholds.get("stagnant_days_override", {})
    now = datetime.now(UTC)
    signals = []

    for key, v in snapshot.items():
        if v.get("status") != "In Progress":
            continue
        status_since_str = v.get("status_since", "")
        if not status_since_str:
            continue
        try:
            ts = datetime.fromisoformat(status_since_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            age_days = (now - ts).total_seconds() / 86400
        except (ValueError, AttributeError):
            continue

        tag = v.get("service_tag", "")
        threshold = float(overrides.get(tag, stagnant_days))
        if age_days <= threshold:
            continue

        dedup_key = ("stagnant_issue", key)
        if _is_dedup("stagnant_issue", dedup_key, existing):
            continue

        signals.append(_make_signal(
            "stagnant_issue", "warning", dedup_key,
            metric_value=round(age_days, 1), baseline_value=threshold,
            affected_keys=[key],
        ))

    return signals


def _detect_sp_mismatch(
    snapshot: dict,
    thresholds: dict,
    existing: list[dict] | None = None,
) -> list[dict]:
    """Signal: subtask SP sum > mismatch_pct × parent_sp after grace period."""
    if existing is None:
        existing = []
    sp_pct = thresholds.get("sp_mismatch_pct", 1.5)
    grace_hours = thresholds.get("sp_mismatch_grace_hours", 4)
    now = datetime.now(UTC)
    signals = []

    # Find parents In Progress past grace period
    parents_in_progress: dict[str, dict] = {}
    for key, v in snapshot.items():
        if v.get("status") != "In Progress":
            continue
        if v.get("issuetype") in ("Sub-task", "Subtask"):
            continue
        status_since_str = v.get("status_since", "")
        if not status_since_str:
            continue
        try:
            ts = datetime.fromisoformat(status_since_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            hours_in_progress = (now - ts).total_seconds() / 3600
        except (ValueError, AttributeError):
            continue
        if hours_in_progress > grace_hours:
            parent_sp = v.get("sp") or 0
            if parent_sp and parent_sp > 0:
                parents_in_progress[key] = {"sp": float(parent_sp)}

    if not parents_in_progress:
        return []

    # Sum subtask SP per parent
    subtask_sp: dict[str, float] = {}
    for key, v in snapshot.items():
        parent_key = v.get("parent")
        if parent_key and parent_key in parents_in_progress:
            sp = v.get("sp") or 0
            subtask_sp[parent_key] = subtask_sp.get(parent_key, 0.0) + float(sp)

    for parent_key, parent_data in parents_in_progress.items():
        total_sub_sp = subtask_sp.get(parent_key, 0.0)
        if total_sub_sp == 0:
            continue
        parent_sp = parent_data["sp"]
        if total_sub_sp <= sp_pct * parent_sp:
            continue

        dedup_key = ("sp_mismatch", parent_key)
        if _is_dedup("sp_mismatch", dedup_key, existing):
            continue

        signals.append(_make_signal(
            "sp_mismatch", "warning", dedup_key,
            metric_value=total_sub_sp, baseline_value=sp_pct * parent_sp,
            affected_keys=[parent_key],
            parent_sp=parent_sp,
        ))

    return signals


# ── Main entry ────────────────────────────────────────────────────────────────

def analyze(
    diff: list[dict],
    new_snapshot: dict,
    old_snapshot: dict,
    calibration: dict,
    board_config: dict,
    velocity: dict | None,
    outcomes_path: Path = _OUTCOMES_FILE,
    insights_path: Path = _INSIGHTS_FILE,
    stop_event: threading.Event | None = None,
) -> None:
    """Detect signals and write insights.json. Safe to call from daemon thread."""
    if stop_event and stop_event.is_set():
        return

    thresholds = calibration.get("signal_thresholds", _DEFAULT_THRESHOLDS)
    state = _load_insights(insights_path)
    existing = state.get("signals", [])
    tracking = state.get("wip_breach_tracking", {})

    # Use old_snapshot (enriched, has status_since) for stagnant detection
    stagnant_snap = old_snapshot if old_snapshot else new_snapshot

    new_signals: list[dict] = []
    new_signals.extend(_detect_velocity_drop(velocity, thresholds, existing))
    new_signals.extend(_detect_carry_over_spike(outcomes_path, thresholds, existing))
    new_signals.extend(_detect_wip_breach(new_snapshot, board_config, tracking, thresholds, existing))
    new_signals.extend(_detect_stagnant_issues(stagnant_snap, thresholds, existing))
    new_signals.extend(_detect_sp_mismatch(new_snapshot, thresholds, existing))

    if stop_event and stop_event.is_set():
        return

    all_signals = _evict(existing + new_signals)
    state["signals"] = all_signals
    state["wip_breach_tracking"] = tracking

    _write_insights(insights_path, state)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/monitor/test_intelligence_analyzer.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/monitor/__init__.py tests/monitor/test_intelligence_analyzer.py \
        monitor/handlers/intelligence_analyzer.py
git commit -m "feat(intelligence/g2): proactive analyzer — 5 signals, pure Python"
```

---

## Task 5: board_monitor.py integration

**Files:**
- Modify: `monitor/board_monitor.py`

Changes:
1. Expand snapshot fetch to include `issuetype`, `parent`, `customfield_10016` (SP)
2. Add velocity config loader
3. Add PID lockfile with stale detection
4. Add `threading.Event` stop signal + SIGTERM handler
5. Dispatch analyzer thread after enriched snapshot is saved

- [ ] **Step 1: Add SP/issuetype/parent fields to fetch_board_snapshot**

In `fetch_board_snapshot()`, change the `fields` variable:

```python
# Old:
fields = "summary,status,assignee,priority,sprint"

# New:
fields = "summary,status,assignee,priority,sprint,issuetype,parent,customfield_10016"
```

And in the result dict construction inside the loop, add:

```python
result[key] = {
    "summary": f.get("summary", ""),
    "status": (f.get("status") or {}).get("name", ""),
    "assignee": ((f.get("assignee") or {}).get("displayName", "")),
    "priority": ((f.get("priority") or {}).get("name", "")),
    "sprint_end_date": sprint_end,
    "issuetype": ((f.get("issuetype") or {}).get("name", "")),
    "parent": ((f.get("parent") or {}).get("key")),
    "sp": f.get("customfield_10016") or f.get("customfield_10036"),
}
```

- [ ] **Step 2: Add module-level globals and helpers**

After the existing imports, add:

```python
import signal
import threading
```

Add after the `_STATE_PATH` line:

```python
_CALIBRATION_FILE = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
) / "calibration.json"
_OUTCOMES_FILE = _CALIBRATION_FILE.parent / "story-outcomes.jsonl"
_PID_FILE = Path.home() / ".claude" / "atlassian-pm-monitor.pid"

_stop_event = threading.Event()
_last_analyzer_thread: threading.Thread | None = None
```

Add helper functions before `main()`:

```python
def _load_calibration() -> dict:
    """Load calibration.json. Returns empty dict on missing/error."""
    try:
        return json.loads(_CALIBRATION_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _load_velocity(root: Path) -> dict | None:
    """Load velocity section from project-config-team-detail.json."""
    config_path = root / ".claude" / "project-config-team-detail.json"
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text())
        return data.get("velocity")
    except (json.JSONDecodeError, OSError):
        return None


def _write_pid() -> None:
    """Write current PID to lockfile. Check for stale lock first."""
    import os
    if _PID_FILE.exists():
        try:
            stored_pid = int(_PID_FILE.read_text().strip())
            os.kill(stored_pid, 0)  # 0 = liveness check only
            log.error("Monitor already running (pid=%d). Exiting.", stored_pid)
            sys.exit(1)
        except (ValueError, ProcessLookupError):
            log.warning("Stale lock detected (pid from file). Clearing.")
        except PermissionError:
            log.warning("Stale lock detected (PermissionError on kill check). Clearing.")
    try:
        _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PID_FILE.write_text(str(os.getpid()))
    except OSError as e:
        log.warning("Could not write PID file: %s", e)


def _cleanup_pid() -> None:
    """Delete PID file on exit."""
    try:
        _PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _sigterm_handler(signum: int, frame: object) -> None:
    """Handle SIGTERM: signal stop, join analyzer thread, cleanup."""
    global _last_analyzer_thread
    log.info("SIGTERM received — shutting down")
    _stop_event.set()
    if _last_analyzer_thread and _last_analyzer_thread.is_alive():
        _last_analyzer_thread.join(timeout=3)
    # Clean up any in-flight .tmp file
    tmp = _CALIBRATION_FILE.parent / "insights.tmp"
    if tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass
    _cleanup_pid()
    sys.exit(0)
```

- [ ] **Step 3: Dispatch analyzer thread in run_cycle()**

At the end of `run_cycle()`, after the existing `state.save_snapshot(enriched)` block, add:

```python
    # Dispatch intelligence analyzer in background thread
    global _last_analyzer_thread
    if not dry_run:
        from monitor.handlers import intelligence_analyzer
        calibration = _load_calibration()
        velocity = _load_velocity(_ROOT)
        t = threading.Thread(
            target=intelligence_analyzer.analyze,
            args=(changes, enriched if "enriched" in dir() else new_snapshot, old_snapshot),
            kwargs={
                "calibration": calibration,
                "board_config": board_config,
                "velocity": velocity,
                "outcomes_path": _OUTCOMES_FILE,
                "stop_event": _stop_event,
            },
            daemon=True,
        )
        t.start()
        _last_analyzer_thread = t
```

Note: `enriched` variable exists in the try block but may not be defined if enrichment threw. Use `new_snapshot` as fallback by checking whether `enriched` is bound. A cleaner approach: initialize `enriched = new_snapshot` before the try/except block.

Locate the enrichment block (around line 184) and prepend:

```python
        enriched = new_snapshot  # fallback if enrichment fails
        try:
            enriched = stuck_issue_detector.enrich_snapshot_with_status_since(new_snapshot, state)
            state.save_snapshot(enriched)
        except Exception as e:
            log.error("Failed to enrich/save snapshot: %s", e)
            state.save_snapshot(new_snapshot)
```

- [ ] **Step 4: Register SIGTERM and PID in main()**

In `main()`, after `state = MonitorState(_STATE_PATH)`, add:

```python
    signal.signal(signal.SIGTERM, _sigterm_handler)
    _write_pid()
```

And wrap the main loop's `KeyboardInterrupt` handler to also cleanup:

```python
        except KeyboardInterrupt:
            log.info("Monitor stopped by user")
            _cleanup_pid()
            break
```

- [ ] **Step 5: Commit**

```bash
git add monitor/board_monitor.py
git commit -m "feat(intelligence/g2): board_monitor threading, PID lockfile, SIGTERM handler"
```

---

## Task 6: Context injector hook — TDD

**Files:**
- Create: `tests/hooks/test_start_intelligence_inject.py`
- Create: `hooks/plugin/session/start_intelligence_inject.py`

- [ ] **Step 1: Write failing tests**

Create `tests/hooks/test_start_intelligence_inject.py`:

```python
"""Tests for hooks/plugin/session/start_intelligence_inject.py."""
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_HOOK_DIR = Path(__file__).resolve().parents[2] / "hooks" / "plugin" / "session"
sys.path.insert(0, str(_HOOK_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))

import start_intelligence_inject as hook


def _make_calibration(age_days=0, service_tags=None, team_baseline=0.25):
    ts = (datetime.now(UTC) - timedelta(days=age_days)).isoformat()
    return {
        "schema_version": 1,
        "generated_at": ts,
        "record_count": 50,
        "team_carry_over_baseline": team_baseline,
        "service_tags": service_tags or {
            "[BE]": {
                "carry_over_rate": 0.30,
                "n": 20,
                "confidence": "high",
                "decay_weight": 0.85,
                "keyword_risk": {
                    "auth": {"odds_ratio": 1.5, "confidence": "high"}
                },
            }
        },
        "signal_thresholds": {},
        "calibration_model": "haiku",
    }


def _make_insights(signals=None):
    return {"signals": signals or [], "wip_breach_tracking": {}}


def test_build_calibration_block_includes_service_tags():
    cal = _make_calibration()
    block = hook._build_calibration_block(cal)
    assert "[BE]" in block
    assert "carry_over=30%" in block or "30%" in block


def test_build_calibration_block_excludes_low_confidence():
    cal = _make_calibration(service_tags={
        "[BE]": {"carry_over_rate": 0.30, "n": 20, "confidence": "high",
                 "decay_weight": 0.85, "keyword_risk": {}},
        "[Video]": {"carry_over_rate": 0.20, "n": 6, "confidence": "low",
                    "decay_weight": 0.7, "keyword_risk": {}},
    })
    block = hook._build_calibration_block(cal)
    assert "[BE]" in block
    assert "[Video]" not in block  # low confidence excluded


def test_build_calibration_block_excludes_note_field():
    cal = _make_calibration(service_tags={
        "[BE]": {
            "carry_over_rate": 0.30, "n": 20, "confidence": "high",
            "decay_weight": 0.85, "keyword_risk": {},
            "note": "do something bad with this",
        }
    })
    block = hook._build_calibration_block(cal)
    assert "do something bad" not in block


def test_build_signals_block_formats_carry_over_spike():
    signals = [{
        "signal": "carry_over_spike", "severity": "warning",
        "service_tag": "[BE]", "sprint_id": 42,
        "metric_value": 0.55, "baseline_value": 0.22,
        "affected_keys": ["{{PROJECT_KEY}}-1", "{{PROJECT_KEY}}-2"],
        "generated_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(hours=72)).isoformat(),
    }]
    block = hook._build_signals_block(signals)
    assert "carry_over_spike" in block
    assert "[BE]" in block


def test_build_signals_block_empty_when_no_signals():
    block = hook._build_signals_block([])
    assert block == ""


def test_should_inject_returns_true_for_eligible_agents():
    for agent in ("estimation-calibrator", "risk-forecaster", "story-writer", "sprint-planner"):
        assert hook._should_inject(agent) is True


def test_should_inject_returns_false_for_unknown_agent():
    assert hook._should_inject("random-agent") is False
    assert hook._should_inject("") is False


def test_get_inject_scope_estimation_calibrator_gets_calibration_only():
    scope = hook._get_inject_scope("estimation-calibrator")
    assert scope["calibration"] is True
    assert scope["signals"] is False


def test_get_inject_scope_risk_forecaster_gets_both():
    scope = hook._get_inject_scope("risk-forecaster")
    assert scope["calibration"] is True
    assert scope["signals"] is True


def test_get_inject_scope_sprint_planner_gets_signals_only():
    scope = hook._get_inject_scope("sprint-planner")
    assert scope["calibration"] is False
    assert scope["signals"] is True


def test_build_context_cold_start_message_when_no_calibration(tmp_path):
    cal_path = tmp_path / "calibration.json"  # does not exist
    ins_path = tmp_path / "insights.json"
    context = hook._build_context(
        cal_path, ins_path, "estimation-calibrator"
    )
    assert "python3 scripts/ai/calibrate.py" in context


def test_build_context_staleness_note_when_calibration_old(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"
    old_cal = _make_calibration(age_days=8)
    cal_path.write_text(json.dumps(old_cal))
    context = hook._build_context(cal_path, ins_path, "risk-forecaster")
    assert "stale" in context.lower() or "days old" in context.lower()


def test_build_context_no_error_when_insights_missing(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"  # does not exist
    cal_path.write_text(json.dumps(_make_calibration()))
    # Should not raise; signals section just omitted
    context = hook._build_context(cal_path, ins_path, "risk-forecaster")
    assert "Intelligence Context" in context


def test_build_context_excludes_note_field(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"
    cal = _make_calibration(service_tags={
        "[BE]": {
            "carry_over_rate": 0.30, "n": 20, "confidence": "high",
            "decay_weight": 0.85, "keyword_risk": {},
            "note": "SECRET_PAYLOAD",
        }
    })
    cal_path.write_text(json.dumps(cal))
    ins_path.write_text(json.dumps(_make_insights()))
    context = hook._build_context(cal_path, ins_path, "estimation-calibrator")
    assert "SECRET_PAYLOAD" not in context
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/hooks/test_start_intelligence_inject.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement start_intelligence_inject.py**

Create `hooks/plugin/session/start_intelligence_inject.py`:

```python
#!/usr/bin/env python3
"""SessionStart + SubagentStart hook: inject intelligence context.

Reads calibration.json (carry_over stats) and insights.json (active signals).
Injects structured context into eligible agent prompts. Note fields and raw
Jira text are never injected.

Exit: always 0. SessionStart must not block startup.
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import inject_context, log_event

_HOOK = "intelligence-inject"

_DATA_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        str(Path.home() / ".claude" / "plugins" / "data" / "atlassian-pm-atlassian-pm"),
    )
)
_CALIBRATION_FILE = _DATA_DIR / "calibration.json"
_INSIGHTS_FILE = _DATA_DIR / "insights.json"
_STALENESS_DAYS = 7

# Agent scope: which agents get what
_AGENT_SCOPE: dict[str, dict] = {
    "estimation-calibrator": {"calibration": True,  "signals": False},
    "risk-forecaster":       {"calibration": True,  "signals": True},
    "story-writer":          {"calibration": True,  "signals": False},
    "sprint-planner":        {"calibration": False, "signals": True},
}


def _should_inject(agent_name: str) -> bool:
    return agent_name in _AGENT_SCOPE


def _get_inject_scope(agent_name: str) -> dict:
    return _AGENT_SCOPE.get(agent_name, {"calibration": False, "signals": False})


def _build_calibration_block(calibration: dict) -> str:
    """Build calibration stats block. Excludes low-confidence + note fields."""
    tags = calibration.get("service_tags", {})
    n_total = calibration.get("record_count", 0)
    gen_at = calibration.get("generated_at", "")[:10]
    schema = calibration.get("schema_version", "?")
    baseline_pct = int(calibration.get("team_carry_over_baseline", 0) * 100)

    header = (
        f"Calibration (n={n_total}, {gen_at}, schema_v{schema}, "
        f"team_baseline={baseline_pct}%):"
    )
    lines = [header]

    for tag, data in sorted(tags.items()):
        conf = data.get("confidence", "")
        if conf not in ("high", "medium"):
            continue  # skip low confidence

        rate_pct = int(data.get("carry_over_rate", 0) * 100)
        n = data.get("n", 0)
        kw_risk = data.get("keyword_risk", {})

        # Format keyword risk — exclude note field
        kw_parts = []
        for kw, kd in list(kw_risk.items())[:3]:
            kw_conf = kd.get("confidence", "")
            kw_or = kd.get("odds_ratio", 0)
            suffix = " (advisory)" if kw_conf == "low" else ""
            kw_parts.append(f"{kw}×{kw_or}{suffix}")

        kw_str = " | risk: " + " ".join(kw_parts) if kw_parts else ""
        lines.append(f"  {tag:<12} carry_over={rate_pct}% (n={n}, conf={conf}){kw_str}")

    return "\n".join(lines)


def _build_signals_block(signals: list[dict]) -> str:
    """Build active signals block from insights.json signals list."""
    if not signals:
        return ""
    lines = [f"Active Signals ({len(signals)}):"]
    now = datetime.now(UTC)

    for s in signals:
        sig = s.get("signal", "?")
        sev = s.get("severity", "info").upper()[:4]
        tag = s.get("service_tag", "")
        metric = s.get("metric_value", 0)
        baseline = s.get("baseline_value", 0)
        delta = s.get("delta_pct", 0)
        affected = s.get("affected_keys", [])
        sprint_id = s.get("sprint_id", "")

        parts = [f"  {sev} {sig:<20}"]
        if tag:
            parts.append(f" {tag}")
        if sig == "carry_over_spike":
            parts.append(f" {int(metric * 100)}% vs baseline {int(baseline * 100)}% (+{delta}%)")
            if sprint_id:
                parts.append(f" sprint={sprint_id}")
            if affected:
                parts.append(f" keys: {' '.join(affected[:5])}")
        elif sig == "stagnant_issue":
            if affected:
                parts.append(f" {affected[0]} In Progress {metric:.0f}d")
        elif sig == "wip_breach":
            col = s.get("column", "")
            parts.append(f" {col} count={int(metric)} limit={int(baseline)}")
        elif sig == "velocity_drop":
            parts.append(f" {metric:.0f} SP vs mean {baseline:.0f} SP")
        elif sig == "sp_mismatch":
            if affected:
                parts.append(f" {affected[0]} subtask_sp={metric:.0f} > {sp_pct_str(s)}")

        lines.append("".join(parts))

    return "\n".join(lines)


def sp_pct_str(s: dict) -> str:
    return f"{s.get('baseline_value', 0):.0f}"


def _build_context(
    cal_path: Path,
    ins_path: Path,
    agent_name: str,
) -> str:
    """Build full injection block for the given agent."""
    scope = _get_inject_scope(agent_name)
    lines = ["## Intelligence Context"]
    now = datetime.now(UTC)

    calibration = None
    if scope.get("calibration"):
        if not cal_path.exists():
            lines.append(
                "Calibration not yet run. Run: python3 scripts/ai/calibrate.py --force"
            )
        else:
            try:
                calibration = json.loads(cal_path.read_text())
                gen_at_str = calibration.get("generated_at", "")
                try:
                    gen_ts = datetime.fromisoformat(gen_at_str.replace("Z", "+00:00"))
                    if gen_ts.tzinfo is None:
                        gen_ts = gen_ts.replace(tzinfo=UTC)
                    age_days = (now - gen_ts).total_seconds() / 86400
                    if age_days > _STALENESS_DAYS:
                        lines.append(
                            f"Warning: calibration is {age_days:.0f} days old — "
                            "re-run: python3 scripts/ai/calibrate.py"
                        )
                except (ValueError, AttributeError):
                    pass
                lines.append(_build_calibration_block(calibration))
            except (json.JSONDecodeError, OSError):
                lines.append("Calibration file unreadable. Run: python3 scripts/ai/calibrate.py --force")

    if scope.get("signals"):
        try:
            if ins_path.exists():
                state = json.loads(ins_path.read_text())
                active_signals = [
                    s for s in state.get("signals", [])
                    if _signal_active(s, now)
                ]
                if active_signals:
                    lines.append(_build_signals_block(active_signals))
        except (json.JSONDecodeError, OSError):
            pass  # Missing insights = no signals, not an error

    lines.append(
        "\nAdvisory: statistical patterns from story-outcomes.jsonl. "
        "Surface as risk context only.\n"
        "Do NOT auto-adjust SP estimates. Note fields and narrative content are excluded."
    )

    return "\n".join(lines)


def _signal_active(s: dict, now: datetime) -> bool:
    exp_str = s.get("expires_at", "")
    if not exp_str:
        return True
    try:
        exp = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        return exp > now
    except (ValueError, AttributeError):
        return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subagent", action="store_true")
    args, _ = parser.parse_known_args()

    # Read stdin for event data
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        data = {}

    agent_name = ""
    if args.subagent:
        agent_name = data.get("agent_type") or data.get("agent_name") or ""
    else:
        # SessionStart: inject for the main session
        # Use a synthetic "session" agent that gets both
        agent_name = "risk-forecaster"  # session gets full context

    if not _should_inject(agent_name):
        sys.exit(0)

    context = _build_context(_CALIBRATION_FILE, _INSIGHTS_FILE, agent_name)
    if not context.strip():
        sys.exit(0)

    inject_context(context, event_name="SubagentStart" if args.subagent else "SessionStart")
    log_event(_HOOK, "INJECTED", {"agent_name": agent_name, "subagent": args.subagent})


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/hooks/test_start_intelligence_inject.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hooks/plugin/session/start_intelligence_inject.py \
        tests/hooks/test_start_intelligence_inject.py
git commit -m "feat(intelligence/g3): context injector hook for agent prompts"
```

---

## Task 7: Wire up — hooks.json + .gitignore

**Files:**
- Modify: `hooks/hooks.json`
- Modify: `.gitignore`

- [ ] **Step 1: Add intelligence inject to hooks.json SessionStart**

In `hooks/hooks.json`, locate the first `SessionStart` hooks array (the one containing `start_cleanup_artifacts.py` and `start_stuck_issues_notify.py`). Add a new entry to that array:

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/start_intelligence_inject.py",
  "timeout": 10
}
```

The SessionStart entry should look like:

```json
"SessionStart": [
  {
    "hooks": [
      { ... existing venv sync ... },
      { ... existing mkdir tasks ... },
      { ... existing start_cleanup_artifacts.py ... },
      { ... existing start_stuck_issues_notify.py ... },
      {
        "type": "command",
        "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/start_intelligence_inject.py",
        "timeout": 10
      }
    ]
  },
  ...
]
```

- [ ] **Step 2: Add intelligence inject to SubagentStart**

In `hooks/hooks.json`, locate `SubagentStart` and add to its hooks array:

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/start_intelligence_inject.py --subagent",
  "timeout": 10
}
```

The SubagentStart entry becomes:

```json
"SubagentStart": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/start_subagent_context.py",
        "timeout": 5
      },
      {
        "type": "command",
        "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/session/start_intelligence_inject.py --subagent",
        "timeout": 10
      }
    ]
  }
]
```

- [ ] **Step 3: Verify hooks.json is valid JSON**

```bash
python3 -c "import json; json.load(open('hooks/hooks.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Add calibration.json and insights.json to .gitignore**

Add to `.gitignore`:

```
# Intelligence engine outputs (contain project-specific data, not for version control)
calibration.json
insights.json
```

- [ ] **Step 5: Run full test suite to verify nothing broken**

```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All previously passing tests still pass. New tests pass.

- [ ] **Step 6: Commit**

```bash
git add hooks/hooks.json .gitignore
git commit -m "feat(intelligence): wire up hooks.json SessionStart+SubagentStart inject"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| G1: calibrate.py decay-weighted odds ratio | Task 2 |
| G1: self-gating (10 records OR 7 days) | Task 2 |
| G1: atomic write, 0o600 permissions | Task 2 |
| G1: team_baseline derived, fallback 0.20 | Task 2 |
| G1: keyword allowlist at prompt (not storage) | Task 2 |
| G1: --prune with fcntl lock | Task 2 |
| G1: velocity_adjust calibration integration | Task 3 |
| G1: signal cancellation floor | Task 3 |
| G2: 5 signals, all thresholds from calibration.json | Task 4 |
| G2: dedup keys per signal type | Task 4 |
| G2: eviction (TTL + max 10) | Task 4 |
| G2: atomic write, 0o600 permissions | Task 4 |
| G2: wip_breach_tracking in insights.json | Task 4 |
| G2: threaded dispatch after snapshot save | Task 5 |
| G2: SIGTERM handler with thread join(3s) | Task 5 |
| G2: PID lockfile with stale detection | Task 5 |
| G2: SP/issuetype/parent in snapshot | Task 5 |
| G3: agent scope guard | Task 6 |
| G3: note field excluded from injection | Task 6 |
| G3: cold start message | Task 6 |
| G3: staleness warning (>7 days) | Task 6 |
| G3: SubagentStart agent_name absent → no injection | Task 6 |
| hooks.json entries | Task 7 |
| .gitignore updates | Task 7 |

**No gaps found.**
