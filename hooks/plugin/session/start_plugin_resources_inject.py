#!/usr/bin/env python3
"""SessionStart: Inject compact plugin resources context once per session.

Trigger: SessionStart event (all sessions).
Guard:   Runs only once per session — skipped on subsequent triggers using
         a session-state flag file (/tmp/claude-hooks-state/<session_id>.resources_injected).

Injects a ≤100-line block listing:
  - Available skills (name + one-line description from SKILL.md frontmatter)
  - Script categories (scripts/api, scripts/ai, scripts/analysis) with counts
  - Core HR rules summary (HR5, HR6, HR7, HR10)

Reads from CLAUDE_PLUGIN_ROOT env var; falls back to resolving from __file__.
Silent exit 0 on any error — must never block session start.
"""

import json
import os
import re
import sys
from pathlib import Path

# ── Path bootstrap ─────────────────────────────────────────────────────────

def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env)
    # __file__ is hooks/plugin/session/start_plugin_resources_inject.py
    # plugin root is 3 levels up
    return Path(__file__).resolve().parents[3]


PLUGIN_ROOT = _plugin_root()

sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from hooks_lib import inject_context  # noqa: E402

# ── Session guard ──────────────────────────────────────────────────────────

_STATE_DIR = Path("/tmp/claude-hooks-state")


def _already_injected(session_id: str) -> bool:
    flag = _STATE_DIR / f"{session_id}.resources_injected"
    return flag.exists()


def _mark_injected(session_id: str) -> None:
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        (_STATE_DIR / f"{session_id}.resources_injected").touch()
    except OSError:
        pass


# ── Skills reader ──────────────────────────────────────────────────────────

_DESCRIPTION_RE = re.compile(r"^description:\s*[|>]?\s*(.+)", re.MULTILINE)
_FRONTMATTER_END_RE = re.compile(r"^---\s*$", re.MULTILINE)


def _extract_skill_description(skill_md: Path) -> str:
    """Return first non-empty line of the description field from SKILL.md frontmatter."""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        # Only look inside frontmatter (between first two ---)
        parts = _FRONTMATTER_END_RE.split(text, maxsplit=2)
        frontmatter = parts[1] if len(parts) >= 3 else text

        m = _DESCRIPTION_RE.search(frontmatter)
        if not m:
            return ""
        first_line = m.group(1).strip()
        if first_line:
            return first_line[:100]
        # Block scalar: description is on subsequent indented lines
        after = text[m.end():]
        for line in after.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("-"):
                return stripped[:100]
        return ""
    except OSError:
        return ""


def _collect_skills(plugin_root: Path) -> list[tuple[str, str]]:
    """Return [(skill_name, description), ...] sorted by name."""
    skills_dir = plugin_root / "skills"
    if not skills_dir.is_dir():
        return []
    results: list[tuple[str, str]] = []
    for category_dir in sorted(skills_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        for skill_dir in sorted(category_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            desc = _extract_skill_description(skill_md)
            results.append((skill_dir.name, desc))
    return results


# ── Scripts reader ─────────────────────────────────────────────────────────

def _count_scripts(plugin_root: Path, subdir: str) -> int:
    d = plugin_root / "scripts" / subdir
    if not d.is_dir():
        return 0
    return sum(1 for f in d.iterdir() if f.suffix == ".py" and f.name != "__init__.py")


# ── Context builder ────────────────────────────────────────────────────────

def _build_context(plugin_root: Path) -> str:
    lines: list[str] = ["## Plugin Resources (atlassian-pm)"]

    # Skills
    skills = _collect_skills(plugin_root)
    if skills:
        lines.append(f"\n### Skills ({len(skills)} available) — invoke via `/atlassian-pm:<name>`")
        for name, desc in skills:
            suffix = f" — {desc}" if desc else ""
            lines.append(f"  - {name}{suffix}")
    else:
        lines.append("\n### Skills — run `ls skills/` to list available skills")

    # Scripts
    lines.append("\n### Scripts (python3 scripts/<category>/<file>.py)")
    for subdir in ("api", "ai", "analysis"):
        count = _count_scripts(plugin_root, subdir)
        if count:
            lines.append(f"  - scripts/{subdir}/  ({count} scripts)")

    # HR rules summary
    lines.append(
        "\n### Core HR Rules (Hard — violating = data corruption)\n"
        "  - HR5: After MCP subtask create → verify parent with jira_get_issue(fields='parent')\n"
        "  - HR6: After ANY Jira write → cache_invalidate(issue_key, auto_refresh=true)\n"
        "  - HR7: Sprint ID NEVER hardcoded — jira_get_sprints_from_board(board_id, state='active')\n"
        "  - HR10: NEVER set sprint field on subtasks (customfield_10020) — inherited from parent"
    )

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        # Read session_id from stdin (may be empty for SessionStart)
        try:
            raw = sys.stdin.read()
            data = json.loads(raw) if raw.strip() else {}
        except (json.JSONDecodeError, OSError):
            data = {}

        session_id = data.get("session_id", "default")

        if _already_injected(session_id):
            sys.exit(0)

        context = _build_context(PLUGIN_ROOT)
        _mark_injected(session_id)
        inject_context(context, event_name="SessionStart")
    except Exception:
        pass  # never block session start

    sys.exit(0)


if __name__ == "__main__":
    main()
