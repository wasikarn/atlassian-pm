#!/usr/bin/env python3
"""UserPromptSubmit: Suggest apm-pretty-mermaid skill when prompt mentions mermaid.

Trigger: UserPromptSubmit event.
Match:   Word-boundary regex \bmermaid\b (case-insensitive) on prompt.text field.

If matched, injects an additionalContext tip pointing to the correct skills:
  - /atlassian-pm:apm-pretty-mermaid for Jira ADF
  - /atlassian-pm:atlassian-scripts for Confluence macro-aware scripts

Silent exit 0 on no match or any error.
Must be fast (<50ms) — no network calls, no disk I/O beyond stdin read.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
from hooks_lib import allow, inject_context, parse_stdin

_MERMAID_RE = re.compile(r"\bmermaid\b", re.IGNORECASE)

_HINT = (
    "TIP: For rendering Mermaid diagrams compatible with Jira ADF, use "
    "`/atlassian-pm:apm-pretty-mermaid`. "
    "For Confluence use `/atlassian-pm:atlassian-scripts` → macro-aware scripts."
)


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    # UserPromptSubmit payload: prompt is nested under "prompt" key
    prompt_obj = data.get("prompt") or {}
    if isinstance(prompt_obj, str):
        prompt_text = prompt_obj
    else:
        prompt_text = prompt_obj.get("text", "") or ""

    # Fallback: some runtimes put text at top-level
    if not prompt_text:
        prompt_text = data.get("text", "") or ""

    if not _MERMAID_RE.search(prompt_text):
        allow()
        return

    inject_context(_HINT, event_name="UserPromptSubmit")


if __name__ == "__main__":
    main()
