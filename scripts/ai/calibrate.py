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
import os
import re
import sys
import threading
from datetime import UTC, datetime
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
_LOCK_FILE = _DATA_DIR / "calibration.lock"
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
    # Read line count before acquiring lock to avoid unnecessary contention
    try:
        with open(path) as fh:
            lines = fh.readlines()
        if len(lines) <= keep:
            return
    except OSError:
        return
    tmp = Path(str(path) + ".tmp")
    try:
        with open(path, "r+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                lines = fh.readlines()  # re-read under lock (may have changed)
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


def _hard_timeout(seconds: int = 60) -> threading.Timer:
    """Kill the process if calibration takes too long (fire-and-forget protection)."""
    def _kill() -> None:
        os._exit(1)
    t = threading.Timer(seconds, _kill)
    t.daemon = True
    t.start()
    return t


def run_calibration(
    outcomes_path: Path = _OUTCOMES_FILE,
    calibration_path: Path = _CALIBRATION_FILE,
    lock_file: Path = _LOCK_FILE,
    force: bool = False,
) -> dict | None:
    """Run calibration. Returns result dict or None if skipped/no data."""
    timer = _hard_timeout(60)
    # Use "a" mode — avoids truncating the lock file on open (no-truncate is conventional
    # for lock files). mode 0o600: lock file holds no sensitive data but should not be
    # world-readable per least-privilege principle.
    lock_fd = open(lock_file, "a", opener=lambda p, f: os.open(p, f, 0o600))
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        # Early cancel: timer is no longer needed since we're exiting immediately.
        # The finally block below would also cancel it, but this makes intent explicit.
        timer.cancel()
        lock_fd.close()
        return None  # another calibration is running — exit cleanly
    try:
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
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        timer.cancel()


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
