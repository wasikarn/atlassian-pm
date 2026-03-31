"""Tests for scripts/ai/calibrate.py."""
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai"))
import calibrate  # type: ignore[import-untyped]


def _make_record(service_tag, outcome, age_days=0, summary="fix auth bug"):
    ts = (datetime.now(UTC) - timedelta(days=age_days)).isoformat()
    return json.dumps({
        "ts": ts, "sprint_id": "1", "sprint_name": "S1",
        "issue_key": "TP-1", "summary": summary,
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
    calibrate.run_calibration(
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


# ── _hard_timeout ─────────────────────────────────────────────────────────────

class _FakeTimer:
    def __init__(self, interval, fn):
        self.interval = interval
        self.fn = fn
        self.daemon = False
        self._started = False
        self._cancelled = False
    def start(self):
        self._started = True
    def cancel(self):
        self._cancelled = True


def test_hard_timeout_creates_started_daemon_timer(monkeypatch):
    captured = []
    def fake_timer(interval, fn):
        t = _FakeTimer(interval, fn)
        captured.append(t)
        return t
    monkeypatch.setattr(calibrate.threading, "Timer", fake_timer)
    t = calibrate._hard_timeout(30)
    assert len(captured) == 1
    assert captured[0].interval == 30
    assert captured[0].daemon is True
    assert captured[0]._started is True
    t.cancel()
    assert captured[0]._cancelled is True


# ── run_calibration flock ──────────────────────────────────────────────────────

def test_run_calibration_returns_none_when_lock_held(tmp_path, monkeypatch):
    """When another process holds the lock, run_calibration returns None immediately."""
    def locked_flock(*_: object) -> None:
        raise BlockingIOError("lock held by another process")
    monkeypatch.setattr(calibrate.fcntl, "flock", locked_flock)
    monkeypatch.setattr(calibrate, "_hard_timeout", lambda *_: _FakeTimer(60, lambda: None))

    outcomes = _write_outcomes(tmp_path, [_make_record("BE", "completed")] * 15)
    cal_path = tmp_path / "calibration.json"
    lock_path = tmp_path / "calibration.lock"

    result = calibrate.run_calibration(
        outcomes_path=outcomes,
        calibration_path=cal_path,
        lock_file=lock_path,
        force=True,
    )
    assert result is None
    assert not cal_path.exists()


def test_run_calibration_cancels_timer_on_success(tmp_path, monkeypatch):
    """Timer is cancelled after successful calibration, and calibration.json is written."""
    timer = _FakeTimer(60, lambda: None)
    monkeypatch.setattr(calibrate, "_hard_timeout", lambda *_: timer)
    # Use real flock — lock_path in tmp_path is isolated
    outcomes = _write_outcomes(tmp_path, [_make_record("BE", "completed")] * 6)
    cal_path = tmp_path / "calibration.json"
    lock_path = tmp_path / "calibration.lock"

    result = calibrate.run_calibration(
        outcomes_path=outcomes,
        calibration_path=cal_path,
        lock_file=lock_path,
        force=True,
    )
    # Verify calibration actually ran (not just early-exited)
    assert result is not None
    assert cal_path.exists()
    assert timer._cancelled is True
