"""Tests for hooks/plugin/session/start_intelligence_inject.py."""
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
_HOOK_DIR = Path(__file__).resolve().parents[2] / "hooks" / "plugin" / "session"
sys.path.insert(0, str(_HOOK_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))

import start_intelligence_inject as hook  # type: ignore[import-untyped]


def _make_calibration(age_days=0, service_tags=None, team_baseline=0.25):
    ts = (datetime.now(UTC) - timedelta(days=age_days)).isoformat()
    return {
        "schema_version": 1,
        "generated_at": ts,
        "record_count": 50,
        "team_carry_over_baseline": team_baseline,
        "service_tags": service_tags or {
            "[BE]": {
                "carry_over_rate": 0.40, "n": 20, "confidence": "high",
                "decay_weight": 0.85, "keyword_risk": {
                    "auth": {"odds_ratio": 1.8, "confidence": "medium"},
                }
            },
            "[FE-Admin]": {
                "carry_over_rate": 0.20, "n": 12, "confidence": "medium",
                "decay_weight": 0.90, "keyword_risk": {},
            },
        },
        "signal_thresholds": {},
        "calibration_model": "haiku",
    }


def _make_insights(signals=None):
    now = datetime.now(UTC)
    return {
        "signals": signals or [
            {
                "signal": "carry_over_spike",
                "severity": "warning",
                "metric_value": 0.60,
                "baseline_value": 0.40,
                "delta_pct": 50,
                "affected_keys": ["TP-1", "TP-2"],
                "generated_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=24)).isoformat(),
                "service_tag": "[BE]",
                "sprint_id": "42",
                "_dedup_key": ["carry_over_spike", "[BE]", "42"],
            }
        ],
        "wip_breach_tracking": {},
    }


# ── _should_inject ─────────────────────────────────────────────────────────────

def test_should_inject_risk_forecaster():
    assert hook._should_inject("risk-forecaster") is True


def test_should_inject_estimation_calibrator():
    assert hook._should_inject("estimation-calibrator") is True


def test_should_inject_session():
    assert hook._should_inject("session") is True


def test_should_inject_unknown_returns_false():
    assert hook._should_inject("unknown-agent") is False


def test_should_inject_empty_string_returns_false():
    assert hook._should_inject("") is False


# ── _build_calibration_block ───────────────────────────────────────────────────

def test_build_calibration_block_includes_high_confidence(tmp_path):
    cal_path = tmp_path / "calibration.json"
    cal = _make_calibration()
    cal_path.write_text(json.dumps(cal))
    calibration = json.loads(cal_path.read_text())
    block = hook._build_calibration_block(calibration)
    assert "[BE]" in block
    assert "carry_over=40%" in block


def test_build_calibration_block_skips_low_confidence():
    cal = _make_calibration(service_tags={
        "[BE]": {"carry_over_rate": 0.50, "n": 4, "confidence": "low",
                 "decay_weight": 0.9, "keyword_risk": {}}
    })
    block = hook._build_calibration_block(cal)
    assert "[BE]" not in block


def test_build_calibration_block_excludes_note_field():
    cal = _make_calibration(service_tags={
        "[BE]": {
            "carry_over_rate": 0.30, "n": 20, "confidence": "high",
            "decay_weight": 0.85, "keyword_risk": {},
            "note": "SECRET_PAYLOAD",
        }
    })
    block = hook._build_calibration_block(cal)
    assert "SECRET_PAYLOAD" not in block


# ── _build_signals_block ───────────────────────────────────────────────────────

def test_build_signals_block_formats_carry_over_spike():
    insights = _make_insights()
    signals = insights["signals"]
    block = hook._build_signals_block(signals)
    assert "carry_over_spike" in block
    assert "60%" in block


def test_build_signals_block_empty_returns_empty():
    block = hook._build_signals_block([])
    assert block == ""


# ── _build_context ─────────────────────────────────────────────────────────────

def test_build_context_includes_calibration_for_risk_forecaster(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"
    cal_path.write_text(json.dumps(_make_calibration()))
    ins_path.write_text(json.dumps(_make_insights()))
    context = hook._build_context(cal_path, ins_path, "risk-forecaster")
    assert "Intelligence Context" in context
    assert "[BE]" in context


def test_build_context_includes_signals_for_risk_forecaster(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"
    cal_path.write_text(json.dumps(_make_calibration()))
    ins_path.write_text(json.dumps(_make_insights()))
    context = hook._build_context(cal_path, ins_path, "risk-forecaster")
    assert "carry_over_spike" in context


def test_build_context_no_signals_for_estimation_calibrator(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"
    cal_path.write_text(json.dumps(_make_calibration()))
    ins_path.write_text(json.dumps(_make_insights()))
    context = hook._build_context(cal_path, ins_path, "estimation-calibrator")
    assert "Intelligence Context" in context
    assert "carry_over_spike" not in context


def test_build_context_cold_start_message_when_calibration_missing(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"
    # calibration.json does NOT exist
    context = hook._build_context(cal_path, ins_path, "estimation-calibrator")
    assert "not yet run" in context.lower() or "calibration" in context.lower()


def test_build_context_staleness_warning_when_old(tmp_path):
    cal_path = tmp_path / "calibration.json"
    ins_path = tmp_path / "insights.json"
    old_cal = _make_calibration(age_days=8)  # 8 > 7 day threshold
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
