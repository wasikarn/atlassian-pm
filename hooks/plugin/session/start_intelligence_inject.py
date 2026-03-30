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
    "session":               {"calibration": True,  "signals": False},  # main SessionStart context
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


def _sp_pct_str(s: dict) -> str:
    """Format baseline SP value for sp_mismatch signal display."""
    return f"{s.get('baseline_value', 0):.0f}"


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
                parts.append(f" {affected[0]} subtask_sp={metric:.0f} > {_sp_pct_str(s)}")

        lines.append("".join(parts))

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
        # SessionStart: inject calibration stats only (no raw Jira signals in main session)
        agent_name = "session"

    if not _should_inject(agent_name):
        sys.exit(0)

    context = _build_context(_CALIBRATION_FILE, _INSIGHTS_FILE, agent_name)
    if not context.strip():
        sys.exit(0)

    inject_context(context, event_name="SubagentStart" if args.subagent else "SessionStart")
    log_event(_HOOK, "INJECTED", {"agent_name": agent_name, "subagent": args.subagent})


if __name__ == "__main__":
    main()
