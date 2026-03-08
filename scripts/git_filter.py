#!/usr/bin/env python3
"""Git smudge/clean filter for project-config placeholders.

Configured via .gitattributes + git config (see scripts/setup.sh):
  smudge: placeholder → real values  (on checkout/pull)
  clean:  real values → placeholder  (on add/commit)

If .claude/project-config.json is missing, passes through unchanged.
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / ".claude" / "project-config.json"


def load_values():
    """Load config values. Returns None if config missing."""
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH) as f:
        c = json.load(f)

    # Build member name → slot mapping from team.members[]
    members = c.get("team", {}).get("members", [])
    member_slots = {}
    for i, m in enumerate(members):
        name = m.get("name")
        if name:
            member_slots[name] = f"SLOT_{i + 1}"

    return {
        "PROJECT_KEY": c["jira"]["project_key"],
        "JIRA_SITE": c["jira"]["site"],
        "CONFLUENCE_SITE": c["confluence"]["site"],
        "START_DATE_FIELD": c["jira"]["custom_fields"]["start_date"],
        "SPRINT_FIELD": c["jira"]["custom_fields"]["sprint"],
        "COMPANY": c.get("company", "Tathep"),
        "COMPANY_LOWER": c.get("company_lower", "tathep"),
        "MEMBER_SLOTS": member_slots,
    }


def smudge(content, v):
    """Placeholder → real values (checkout/pull)."""
    pk = v["PROJECT_KEY"]

    # PROJECT_KEY
    content = re.sub(r'"projectKey":\s*"\{\{PROJECT_KEY\}\}"', f'"projectKey": "{pk}"', content)
    content = re.sub(r'project_key:\s*"\{\{PROJECT_KEY\}\}"', f'project_key: "{pk}"', content)
    content = re.sub(r'project_key="\{\{PROJECT_KEY\}\}"', f'project_key="{pk}"', content)
    content = re.sub(r'space_key:\s*"\{\{SPACE_KEY\}\}"', f'space_key: "{pk}"', content)
    content = re.sub(r'space_key="\{\{SPACE_KEY\}\}"', f'space_key="{pk}"', content)
    content = re.sub(r"\{\{PROJECT_KEY\}\}-XXX", f"{pk}-XXX", content)

    # JIRA_SITE
    content = re.sub(r"https://\{\{JIRA_SITE\}\}", f"https://{v['JIRA_SITE']}", content)

    # CONFLUENCE_SITE
    content = re.sub(r"https://\{\{CONFLUENCE_SITE\}\}", f"https://{v['CONFLUENCE_SITE']}", content)

    # Custom fields
    content = re.sub(r"\{\{START_DATE_FIELD\}\}", v["START_DATE_FIELD"], content)
    content = re.sub(r"\{\{SPRINT_FIELD\}\}", v["SPRINT_FIELD"], content)

    # COMPANY
    content = re.sub(r"\{\{COMPANY\}\} Platform", f"{v['COMPANY']} Platform", content)
    content = re.sub(r"for \*\*\{\{COMPANY\}\} Platform\*\*", f"for **{v['COMPANY']} Platform**", content)
    content = re.sub(
        r"Agile Documentation System for \*\*\{\{COMPANY\}\}",
        f"Agile Documentation System for **{v['COMPANY']}",
        content,
    )

    # COMPANY_LOWER
    content = re.sub(
        r"~/Projects/\{\{COMPANY_LOWER\}\}/",
        f"~/Codes/Works/{v['COMPANY_LOWER']}/",
        content,
    )

    # Team member names: {{SLOT_N}} → real name
    for name, slot in v["MEMBER_SLOTS"].items():
        content = content.replace(f"{{{{{slot}}}}}", name)

    return content


def clean(content, v):
    """Real values → placeholder (add/commit)."""
    pk = re.escape(v["PROJECT_KEY"])

    # PROJECT_KEY
    content = re.sub(rf'"projectKey":\s*"{pk}"', '"projectKey": "{{PROJECT_KEY}}"', content)
    content = re.sub(rf'project_key:\s*"{pk}"', 'project_key: "{{PROJECT_KEY}}"', content)
    content = re.sub(rf'project_key="{pk}"', 'project_key="{{PROJECT_KEY}}"', content)
    content = re.sub(rf'space_key:\s*"{pk}"', 'space_key: "{{SPACE_KEY}}"', content)
    content = re.sub(rf'space_key="{pk}"', 'space_key="{{SPACE_KEY}}"', content)
    # Issue key pattern (but not in URLs/smart links)
    content = re.sub(rf"(?<!/browse/){pk}-XXX", "{{PROJECT_KEY}}-XXX", content)

    # JIRA_SITE
    content = re.sub(
        rf"https://{re.escape(v['JIRA_SITE'])}",
        "https://{{JIRA_SITE}}",
        content,
    )

    # CONFLUENCE_SITE (only if different from JIRA_SITE)
    if v["CONFLUENCE_SITE"] != v["JIRA_SITE"]:
        content = re.sub(
            rf"https://{re.escape(v['CONFLUENCE_SITE'])}",
            "https://{{CONFLUENCE_SITE}}",
            content,
        )

    # Custom fields
    content = re.sub(re.escape(v["START_DATE_FIELD"]), "{{START_DATE_FIELD}}", content)
    content = re.sub(re.escape(v["SPRINT_FIELD"]), "{{SPRINT_FIELD}}", content)

    # COMPANY
    co = re.escape(v["COMPANY"])
    content = re.sub(rf"{co} Platform", "{{COMPANY}} Platform", content)
    content = re.sub(rf"for \*\*{co} Platform\*\*", "for **{{COMPANY}} Platform**", content)
    content = re.sub(
        rf"Agile Documentation System for \*\*{co}",
        "Agile Documentation System for **{{COMPANY}}",
        content,
    )

    # COMPANY_LOWER
    content = re.sub(
        rf"~/Codes/Works/{re.escape(v['COMPANY_LOWER'])}/",
        "~/Projects/{{COMPANY_LOWER}}/",
        content,
    )

    # Team member names: real name → {{SLOT_N}} (longest first to avoid substring issues)
    for name in sorted(v["MEMBER_SLOTS"], key=len, reverse=True):
        slot = v["MEMBER_SLOTS"][name]
        content = content.replace(name, f"{{{{{slot}}}}}")

    return content


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--smudge"
    content = sys.stdin.buffer.read().decode("utf-8", errors="replace")

    values = load_values()
    if values is None:
        # No config → pass through unchanged
        sys.stdout.buffer.write(content.encode("utf-8"))
        return

    if mode == "--clean":
        content = clean(content, values)
    else:
        content = smudge(content, values)

    sys.stdout.buffer.write(content.encode("utf-8"))


if __name__ == "__main__":
    main()
