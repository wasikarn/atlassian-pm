#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""U: Impact Analysis Suggester — Auto-detect impacted services from story text.

Analyzes story description for service-related keywords and suggests
which service tags are impacted.

Usage:
    echo '{"text": "Create API endpoint for..."}' | python3 impact_suggester.py
    echo '{"story_adf": {...}}' | python3 impact_suggester.py

Input JSON:
    text: Plain text story description (optional)
    story_adf: Story ADF JSON (optional — will extract text from ADF)

Output JSON:
    services: list of {tag, confidence, reasons} sorted by confidence
    impact_table: Suggested service impact table (markdown)
"""

import json
import re
import sys

# Service detection rules: tag → (keywords, weight)
SERVICE_RULES = {
    "BE": {
        "keywords": [
            (r"\bAPI\b", 3),
            (r"\bendpoint\b", 3),
            (r"\bREST\b", 2),
            (r"\bservice\b", 1),
            (r"\bdatabase\b", 2),
            (r"\bDB\b", 2),
            (r"\bmigration\b", 2),
            (r"\bquery\b", 1),
            (r"\brepository\b", 2),
            (r"\bcontroller\b", 2),
            (r"\bvalidat(?:e|ion)\b", 1),
            (r"\bauth(?:entication|orization)?\b", 2),
            (r"\bGET|POST|PUT|DELETE|PATCH\b", 2),
            (r"\bpayload\b", 1),
            (r"\bresponse\b", 1),
            (r"\brequest\b", 1),
            (r"\bschema\b", 1),
            (r"\bmodel\b", 1),
            (r"\bNestJS\b", 2),
            (r"\bTypeORM\b", 2),
            (r"\bPrisma\b", 2),
        ],
        "threshold": 3,
    },
    "FE-Admin": {
        "keywords": [
            (r"\b[Aa]dmin\b", 3),
            (r"\bbackoffice\b", 3),
            (r"\bCMS\b", 2),
            (r"\bdashboard\b", 2),
            (r"\bจัดการ\b", 2),  # "manage" in Thai
            (r"\bmanage\b", 1),
            (r"\btable\b", 1),
            (r"\bfilter\b", 1),
            (r"\bsearch\b", 1),
            (r"\bform\b", 1),
            (r"\bmodal\b", 1),
            (r"\bAdmin UI\b", 3),
        ],
        "threshold": 3,
    },
    "FE-Web": {
        "keywords": [
            (r"\b[Ww]eb\b", 2),
            (r"\b[Uu]ser\b", 1),
            (r"\bUI\b", 1),
            (r"\bcomponent\b", 2),
            (r"\bpage\b", 1),
            (r"\bหน้า\b", 2),  # "page" in Thai
            (r"\bbutton\b", 1),
            (r"\bปุ่ม\b", 2),  # "button" in Thai
            (r"\bแสดง\b", 1),  # "display" in Thai
            (r"\bdisplay\b", 1),
            (r"\bnavigat(?:e|ion)\b", 1),
            (r"\broute\b", 1),
            (r"\bReact\b", 2),
            (r"\bNext\.js\b", 2),
            (r"\bTailwind\b", 1),
        ],
        "threshold": 3,
    },
    "QA": {
        "keywords": [
            (r"\btest\b", 2),
            (r"\bทดสอบ\b", 2),  # "test" in Thai
            (r"\bQA\b", 3),
            (r"\bscenario\b", 1),
            (r"\bedge case\b", 2),
            (r"\berror handling\b", 2),
        ],
        "threshold": 3,
    },
}


def extract_text_from_adf(adf: dict) -> str:
    """Recursively extract all text from ADF."""
    texts = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(adf)
    return " ".join(texts)


def analyze_impact(text: str) -> list[dict]:
    """Analyze text for service impact."""
    results = []

    for tag, rules in SERVICE_RULES.items():
        score = 0
        reasons = []
        for pattern, weight in rules["keywords"]:
            matches = re.findall(pattern, text, re.I)
            if matches:
                score += weight * len(matches)
                reasons.append(f"{pattern.strip(chr(92)).strip('b')}: {len(matches)}x")

        if score >= rules["threshold"]:
            confidence = min(score / (rules["threshold"] * 3), 1.0)
            results.append(
                {
                    "tag": tag,
                    "score": score,
                    "confidence": round(confidence, 2),
                    "reasons": reasons[:5],
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        sys.exit(1)

    # Get text from input
    text = input_data.get("text", "")
    if not text and "story_adf" in input_data:
        text = extract_text_from_adf(input_data["story_adf"])

    if not text:
        print(json.dumps({"error": "No text provided", "services": []}))
        sys.exit(0)

    services = analyze_impact(text)

    # Generate markdown impact table
    table_lines = ["| Service | Confidence | Key Indicators |", "| --- | --- | --- |"]
    for svc in services:
        indicators = ", ".join(svc["reasons"][:3])
        conf = f"{svc['confidence']:.0%}"
        table_lines.append(f"| [{svc['tag']}] | {conf} | {indicators} |")

    print(
        json.dumps(
            {
                "services": services,
                "suggested_tags": [s["tag"] for s in services],
                "impact_table": "\n".join(table_lines),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
