#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""S: AC-to-Subtask Mapper — Generate subtask ADF drafts from Story ACs.

Reads Story ADF JSON from stdin, extracts AC panels, and generates
subtask ADF templates for each specified service tag.

Usage:
    echo '{"service_tags": ["BE", "FE-Admin"], "story_adf": {...}}' | python3 ac_subtask_mapper.py

Input JSON:
    service_tags: list of tags (e.g. ["BE", "FE-Admin", "FE-Web", "QA"])
    story_adf: Story ADF JSON (description field from Jira)
    story_key: Parent story key (e.g. "BEP-123")
    story_summary: Parent story summary

Output JSON:
    subtasks: list of {tag, summary, adf} subtask drafts
"""

import json
import sys


def extract_acs_from_adf(adf: dict) -> list[dict]:
    """Extract AC panels from ADF content."""
    acs = []
    content = adf.get("content", [])
    for node in content:
        if node.get("type") != "panel":
            continue
        panel_type = node.get("attrs", {}).get("panelType", "")
        if panel_type not in ("success", "warning", "error"):
            continue

        # Extract text from panel
        texts = []
        title = ""
        for child in node.get("content", []):
            if child.get("type") == "paragraph":
                for text_node in child.get("content", []):
                    text = text_node.get("text", "")
                    marks = text_node.get("marks", [])
                    is_bold = any(m.get("type") == "strong" for m in marks)
                    if is_bold and not title:
                        title = text
                    texts.append(text)

        if title:
            acs.append(
                {
                    "title": title,
                    "panel_type": panel_type,
                    "full_text": " ".join(texts),
                }
            )
    return acs


def generate_subtask_adf(tag: str, story_key: str, story_summary: str, acs: list[dict]) -> dict:
    """Generate subtask ADF template for a service tag."""
    # Map AC to service-specific objective
    objectives = {
        "BE": "API logic and business rules",
        "FE-Admin": "Admin UI components and interactions",
        "FE-Web": "Web UI components and interactions",
        "QA": "Test cases covering acceptance criteria",
    }
    objective = objectives.get(tag, f"{tag} implementation")

    # Build AC panels for subtask (max 3)
    ac_panels = []
    for i, ac in enumerate(acs[:3]):
        ac_panels.append(
            {
                "type": "panel",
                "attrs": {"panelType": ac["panel_type"]},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": f"AC{i + 1}: [{tag}] {ac['title']}",
                                "marks": [{"type": "strong"}],
                            },
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
                                            {"type": "text", "text": "Given: ", "marks": [{"type": "strong"}]},
                                            {"type": "text", "text": "[precondition — adapt from story AC]"},
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
                                            {"type": "text", "text": "[action — specific to this service]"},
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
                                            {"type": "text", "text": "[result — specific to this service]"},
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
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "🎯 Objective"}]},
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"[{tag}] {objective} for {story_summary}"},
                ],
            },
            {"type": "rule"},
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "📁 Scope"}]},
            {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Files (New)"}]},
            {
                "type": "table",
                "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
                "content": [
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableHeader",
                                "attrs": {"background": "#e3fcef"},
                                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "File Path"}]}],
                            },
                            {
                                "type": "tableHeader",
                                "attrs": {"background": "#e3fcef"},
                                "content": [
                                    {"type": "paragraph", "content": [{"type": "text", "text": "Description"}]}
                                ],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "[path from codebase explore]",
                                                "marks": [{"type": "code"}],
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "type": "tableCell",
                                "content": [
                                    {"type": "paragraph", "content": [{"type": "text", "text": "[description]"}]}
                                ],
                            },
                        ],
                    },
                ],
            },
            {"type": "rule"},
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "✅ Acceptance Criteria"}]},
            *ac_panels,
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

    return {
        "tag": tag,
        "summary": f"[{tag}] - {story_summary}",
        "adf": adf,
    }


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        sys.exit(1)

    service_tags = input_data.get("service_tags", ["BE", "FE-Admin"])
    story_adf = input_data.get("story_adf", {})
    story_key = input_data.get("story_key", "BEP-XXX")
    story_summary = input_data.get("story_summary", "Feature")

    acs = extract_acs_from_adf(story_adf)
    if not acs:
        print(json.dumps({"error": "No AC panels found in story ADF", "subtasks": []}))
        sys.exit(0)

    subtasks = [generate_subtask_adf(tag, story_key, story_summary, acs) for tag in service_tags]

    print(
        json.dumps(
            {
                "story_key": story_key,
                "ac_count": len(acs),
                "subtask_count": len(subtasks),
                "subtasks": subtasks,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
