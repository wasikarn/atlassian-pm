#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""T: QA Test Matrix Generator — Generate test case ADF from Story ACs.

Reads Story ADF JSON from stdin, extracts AC panels, and generates
a QA subtask ADF with AC coverage matrix and test case panels.

Usage:
    echo '{"story_adf": {...}, "story_key": "BEP-123"}' | python3 qa_matrix_generator.py

Input JSON:
    story_adf: Story ADF JSON (description field from Jira)
    story_key: Parent story key
    story_summary: Parent story summary

Output JSON:
    qa_adf: Complete QA subtask ADF (ready for acli --from-json)
    coverage_matrix: AC → TC mapping
"""

import json
import sys


def extract_acs(adf: dict) -> list[dict]:
    """Extract AC panels from ADF content."""
    acs = []
    content = adf.get("content", [])
    for node in content:
        if node.get("type") != "panel":
            continue
        panel_type = node.get("attrs", {}).get("panelType", "")
        if panel_type not in ("success", "warning", "error"):
            continue

        title = ""
        given = when = then = ""
        for child in node.get("content", []):
            if child.get("type") == "paragraph":
                for tn in child.get("content", []):
                    marks = tn.get("marks", [])
                    is_bold = any(m.get("type") == "strong" for m in marks)
                    text = tn.get("text", "")
                    if is_bold and not title and text.startswith("AC"):
                        title = text
            elif child.get("type") == "bulletList":
                for li in child.get("content", []):
                    for p in li.get("content", []):
                        parts = [t.get("text", "") for t in p.get("content", [])]
                        line = "".join(parts)
                        if "Given:" in line:
                            given = line.replace("Given:", "").strip()
                        elif "When:" in line:
                            when = line.replace("When:", "").strip()
                        elif "Then:" in line:
                            then = line.replace("Then:", "").strip()

        if title:
            acs.append(
                {
                    "title": title,
                    "panel_type": panel_type,
                    "given": given or "[precondition]",
                    "when": when or "[action]",
                    "then": then or "[expected result]",
                }
            )
    return acs


PRIORITY_MAP = {
    "success": "🟠 High",
    "warning": "🟡 Medium",
    "error": "🟠 High",
}

TC_PANEL_MAP = {
    "success": "success",
    "warning": "warning",
    "error": "error",
}


def generate_qa_adf(story_key: str, story_summary: str, acs: list[dict]) -> dict:
    """Generate QA subtask ADF with coverage matrix and test cases."""

    # AC Coverage table rows
    coverage_rows = [
        {
            "type": "tableRow",
            "content": [
                {
                    "type": "tableHeader",
                    "attrs": {"background": "#f4f5f7"},
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "#"}]}],
                },
                {
                    "type": "tableHeader",
                    "attrs": {"background": "#f4f5f7"},
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "AC"}]}],
                },
                {
                    "type": "tableHeader",
                    "attrs": {"background": "#f4f5f7"},
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Scenarios"}]}],
                },
            ],
        },
    ]
    for i, ac in enumerate(acs):
        coverage_rows.append(
            {
                "type": "tableRow",
                "content": [
                    {
                        "type": "tableCell",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(i + 1)}]}],
                    },
                    {
                        "type": "tableCell",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": ac["title"]}]}],
                    },
                    {
                        "type": "tableCell",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"TC{i + 1}"}]}],
                    },
                ],
            }
        )

    # Test Case panels
    tc_panels = []
    for i, ac in enumerate(acs):
        priority = PRIORITY_MAP.get(ac["panel_type"], "🟡 Medium")
        panel_type = TC_PANEL_MAP.get(ac["panel_type"], "success")
        tc_panels.append(
            {
                "type": "panel",
                "attrs": {"panelType": panel_type},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": f"TC{i + 1}: {ac['title']}", "marks": [{"type": "strong"}]},
                        ],
                    },
                    {
                        "type": "bulletList",
                        "content": [
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": f"AC: {i + 1} | Priority: {priority}"},
                                        ],
                                    }
                                ],
                            },
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
                                            {"type": "text", "text": ac["given"]},
                                        ],
                                    }
                                ],
                            },
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": "When: ", "marks": [{"type": "strong"}]},
                                            {"type": "text", "text": ac["when"]},
                                        ],
                                    }
                                ],
                            },
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": "Then: ", "marks": [{"type": "strong"}]},
                                            {"type": "text", "text": ac["then"]},
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            }
        )

    adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🎯 Test Objective"}]},
            {
                "type": "panel",
                "attrs": {"panelType": "info"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": f"Validate acceptance criteria for {story_summary}"},
                        ],
                    },
                ],
            },
            {"type": "rule"},
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📊 AC Coverage"}]},
            {"type": "table", "attrs": {"isNumberColumnEnabled": False, "layout": "default"}, "content": coverage_rows},
            {"type": "rule"},
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🧪 Test Cases"}]},
            *tc_panels,
            {"type": "rule"},
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🔗 Reference"}]},
            {
                "type": "table",
                "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
                "content": [
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableHeader",
                                "attrs": {"background": "#eae6ff"},
                                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Type"}]}],
                            },
                            {
                                "type": "tableHeader",
                                "attrs": {"background": "#eae6ff"},
                                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Link"}]}],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "User Story"}]}],
                            },
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": story_key,
                                                "marks": [
                                                    {
                                                        "type": "link",
                                                        "attrs": {"href": f"https://JIRA_DOMAIN/browse/{story_key}"},
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    }
    return adf


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        sys.exit(1)

    story_adf = input_data.get("story_adf", {})
    story_key = input_data.get("story_key", "BEP-XXX")
    story_summary = input_data.get("story_summary", "Feature")

    acs = extract_acs(story_adf)
    if not acs:
        print(json.dumps({"error": "No AC panels found in story ADF"}))
        sys.exit(0)

    qa_adf = generate_qa_adf(story_key, story_summary, acs)
    coverage = [{"ac": i + 1, "title": ac["title"], "tc": f"TC{i + 1}"} for i, ac in enumerate(acs)]

    print(
        json.dumps(
            {
                "story_key": story_key,
                "ac_count": len(acs),
                "tc_count": len(acs),
                "coverage_matrix": coverage,
                "qa_summary": f"[QA] - Test: {story_summary}",
                "qa_adf": qa_adf,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
