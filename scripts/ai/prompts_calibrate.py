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
