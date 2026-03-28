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


def compute_adjustment(velocity: dict) -> dict:
    """Compute SP adjustment factor from velocity data."""
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

    adjustment_pct = 0
    note = ""

    if trend_pct < -5:
        # Team slowing — reduce estimate to avoid overcommit
        adjustment_pct = max(trend_pct * 0.5, -15)  # cap at -15%
        note = f"team velocity declining {abs(trend_pct):.0f}%"
    elif trend_pct > 5:
        note = f"team velocity improving {trend_pct:.0f}%"

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
    args = parser.parse_args()

    velocity = load_velocity(args.config)
    if velocity is None:
        # No data available — silent exit
        sys.exit(0)
    adj = compute_adjustment(velocity)
    print(format_context(adj))


if __name__ == "__main__":
    main()
