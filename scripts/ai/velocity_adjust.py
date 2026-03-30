#!/usr/bin/env python3
"""Velocity adjustment calculator for SP estimation.

Reads .claude/project-config-team-detail.json and returns velocity context
as a formatted string for injection into estimation prompts.

Usage:
    python3 velocity_adjust.py [--config path/to/config]
    # Prints velocity context string to stdout, or empty string if no data
"""

import argparse
import json
import sys
from pathlib import Path


def load_velocity(config_path: Path | None = None) -> dict | None:
    """Load velocity section from project-config-team-detail.json."""
    if config_path is None:
        # Walk up from cwd to find .claude/project-config-team-detail.json
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            candidate = parent / ".claude" / "project-config-team-detail.json"
            if candidate.exists():
                config_path = candidate
                break
    if config_path is None:
        return None
    try:
        with open(config_path) as f:
            data = json.load(f)
        return data.get("velocity")
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return None


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
    # Support both velocity-tracker schema (story_points.avg_velocity) and
    # flat schema (rolling_average) for forward/backward compatibility.
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


def format_context(adj: dict) -> str:
    """Format velocity context for injection into estimation prompt."""
    lines = [
        f"Velocity Context: avg={adj['rolling_average']:.0f} SP/sprint, "
        f"trend={adj['trend_pct']:+.0f}%, "
        f"std_dev={adj['std_dev']:.1f} SP"
    ]
    if adj["adjustment_pct"] != 0:
        lines.append(
            f"Velocity Adjustment: {adj['adjustment_pct']:+.0f}% "
            f"({adj['note']})"
        )
    elif adj["note"]:
        lines.append(f"Velocity Note: {adj['note']}")
    if adj["high_variance"]:
        lines.append("⚠️  High sprint variance — estimates may be less reliable")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print velocity context for SP estimation prompts"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to project-config-team-detail.json (auto-discovered if omitted)",
    )
    parser.add_argument(
        "--service-tag",
        type=str,
        default=None,
        help="Service tag for calibration lookup (e.g. [BE])",
    )
    args = parser.parse_args()

    velocity = load_velocity(args.config)
    if velocity is None:
        # No data available — silent exit
        sys.exit(0)

    calibration = load_calibration_data()
    adj = compute_adjustment(velocity, calibration=calibration, service_tag=args.service_tag)
    print(format_context(adj))


if __name__ == "__main__":
    main()
