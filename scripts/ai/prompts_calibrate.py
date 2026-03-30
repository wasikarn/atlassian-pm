"""Haiku prompts for calibration note synthesis in calibrate.py."""


def build_calibrate_prompt(service_tags: dict) -> str:
    """Build Haiku prompt with aggregated stats only — no raw Jira text.

    Filters to high/medium confidence tags. Keyword lists are already
    allowlist-filtered before this function is called.
    """
    lines = ["For each service tag below, write one sentence (≤20 words) describing"]
    lines.append("the main carry-over risk pattern. Return JSON: {\"[TAG]\": \"sentence\"}.")
    lines.append("Base your response ONLY on the statistics provided — do not invent patterns.")
    lines.append("")
    lines.append("Stats:")
    for tag, data in service_tags.items():
        if data.get("confidence") not in ("high", "medium"):
            continue
        rate = data.get("carry_over_rate")
        n = data.get("n")
        if rate is None or n is None:
            continue
        rate_pct = int(rate * 100)
        risk_kws = list(data.get("keyword_risk", {}).keys())[:3]
        kw_str = f", risk keywords: {', '.join(risk_kws)}" if risk_kws else ""
        lines.append(f"  {tag}: carry_over={rate_pct}% (n={n}{kw_str})")
    return "\n".join(lines)
