# Claude -p AI Hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phase 1 complete — `hooks/plugin/ai/claude_call.py` must exist.

**Goal:** Replace regex-based hook logic with LLM reasoning via `claude -p` for (1) Thai+English intent detection, (2) semantic AC↔subtask coverage, (3) Explore path quality rating.

**Architecture:** Three async hook scripts in `hooks/plugin/ai/`. Each is `async: true` in `hooks.json` — fires after the existing sync hook, injects enriched context on next turn. Existing sync hooks remain as instant fallback. All hooks exit 0 always (PostToolUse cannot block).

**Tech Stack:** Python stdlib + `hooks/plugin/ai/claude_call.py` + `hooks_lib.inject_context`.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `hooks/plugin/ai/intent_detect.py` | LLM classify issue creation intent (Thai+English) |
| Create | `hooks/plugin/ai/ac_coverage.py` | Semantic AC↔subtask alignment check |
| Create | `hooks/plugin/ai/path_quality.py` | Rate Explore agent path quality |
| Create | `hooks/tests/test_ai_hooks.py` | Unit tests for all 3 hooks (claude_call mocked) |
| Modify | `hooks/hooks.json` | Add async entries for the 3 new hooks |

---

### Task 1: Implement `intent_detect.py`

**Files:**

- Create: `hooks/plugin/ai/intent_detect.py`
- Create: `hooks/tests/test_ai_hooks.py` (start with intent_detect tests)

The existing `pre_prompt_skill_redirect.py` uses regex. This async hook fires additionally (not instead) and can catch cases the regex misses. It injects a stronger reminder if LLM agrees intent is issue creation.

- [ ] **Step 1: Write failing tests**

Create `hooks/tests/test_ai_hooks.py`:

```python
#!/usr/bin/env python3
"""Tests for hooks/plugin/ai/*.py (claude_call mocked)"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugin.ai.intent_detect import classify_intent, main as intent_main
from plugin.ai.ac_coverage import check_coverage, main as coverage_main
from plugin.ai.path_quality import rate_paths, main as paths_main


class TestIntentDetect(unittest.TestCase):

    def _stdin(self, prompt: str) -> str:
        return json.dumps({"prompt": prompt, "session_id": "s1",
                           "hook_event_name": "UserPromptSubmit"})

    def test_detects_bug_creation_thai(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value="bug"):
            result = classify_intent("มีบัคใน login ต้องสร้าง ticket")
        self.assertEqual(result, "bug")

    def test_detects_story_creation_english(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value="story"):
            result = classify_intent("I need a user story for the checkout flow")
        self.assertEqual(result, "story")

    def test_returns_none_when_claude_unavailable(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value=None):
            result = classify_intent("create a bug")
        self.assertIsNone(result)

    def test_returns_none_for_unrelated_prompt(self):
        with patch("plugin.ai.intent_detect.claude_call", return_value="none"):
            result = classify_intent("what is the weather today")
        self.assertIsNone(result)

    def test_main_exits_0_on_empty_stdin(self):
        import io
        with patch("sys.stdin", io.StringIO("")):
            with self.assertRaises(SystemExit) as ctx:
                intent_main()
        self.assertEqual(ctx.exception.code, 0)


class TestAcCoverage(unittest.TestCase):

    def test_returns_score_when_claude_responds(self):
        with patch("plugin.ai.ac_coverage.claude_call", return_value="72"):
            score = check_coverage(["AC1: user can login", "AC2: user can logout"],
                                   ["subtask: implement login", "subtask: implement logout"])
        self.assertEqual(score, 72)

    def test_returns_none_when_claude_unavailable(self):
        with patch("plugin.ai.ac_coverage.claude_call", return_value=None):
            score = check_coverage(["AC1"], ["subtask1"])
        self.assertIsNone(score)

    def test_skips_when_no_acs(self):
        score = check_coverage([], ["subtask1"])
        self.assertIsNone(score)


class TestPathQuality(unittest.TestCase):

    def test_returns_poor_rating(self):
        with patch("plugin.ai.path_quality.claude_call", return_value="poor"):
            rating = rate_paths(["src/", "lib/", "utils/"])
        self.assertEqual(rating, "poor")

    def test_returns_none_when_claude_unavailable(self):
        with patch("plugin.ai.path_quality.claude_call", return_value=None):
            rating = rate_paths(["src/"])
        self.assertIsNone(rating)

    def test_skips_when_no_paths(self):
        rating = rate_paths([])
        self.assertIsNone(rating)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify fail**

```bash
python3 -m pytest hooks/tests/test_ai_hooks.py -v 2>&1 | head -15
```

Expected: `ImportError: No module named 'plugin.ai.intent_detect'`

- [ ] **Step 3: Implement `intent_detect.py`**

Create `hooks/plugin/ai/intent_detect.py`:

```python
#!/usr/bin/env python3
"""UserPromptSubmit async hook: LLM-based intent detection for issue creation.

Fires async alongside pre_prompt_skill_redirect.py (which uses regex).
Catches Thai/English variants the regex misses.
Injects a stronger redirect reminder if LLM confirms issue creation intent.

Exit code: 0 always.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin
from plugin.ai.claude_call import claude_call

_HOOK = "ai-intent-detect"

_SKILL_MAP = {
    "bug":     ("atlassian-pm:bug-triage",   "bug/defect triage → severity → duplicate check → ADF → QG ≥ 90%"),
    "story":   ("atlassian-pm:create-story", "discovery → INVEST → QG ≥ 90% → subtask design"),
    "epic":    ("atlassian-pm:create-epic",  "scope definition → ADF → QG ≥ 90%"),
    "subtask": ("atlassian-pm:create-story", "Part B of create-story handles subtask design"),
    "task":    ("atlassian-pm:create-task",  "scoping → ADF → QG ≥ 90%"),
}

_CLASSIFY_PROMPT = """\
Classify the following user message. Does it express intent to CREATE a Jira issue?
If yes, respond with exactly one word from: bug story epic subtask task
If no or unclear, respond with exactly: none

User message: {prompt}

Respond with one word only."""


def classify_intent(prompt: str) -> str | None:
    """Return issue type string or None if no creation intent detected."""
    result = claude_call(_CLASSIFY_PROMPT.format(prompt=prompt[:500]), timeout=10)
    if not result:
        return None
    classification = result.strip().lower().split()[0] if result.strip() else "none"
    return classification if classification in _SKILL_MAP else None


def main() -> None:
    data = parse_stdin()
    if not data:
        sys.exit(0)

    prompt = data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    issue_type = classify_intent(prompt)
    if not issue_type:
        log_event(_HOOK, "SKIP", {"reason": "no_intent_or_unavailable"})
        allow()
        return

    skill_name, hint = _SKILL_MAP[issue_type]
    log_event(_HOOK, "DETECTED", {"type": issue_type, "skill": skill_name})

    inject_context(
        f"<important-reminder>AI INTENT CONFIRMED — {issue_type.upper()} CREATION DETECTED\n"
        f"You MUST invoke `/{skill_name}` via the Skill tool BEFORE any Jira write.\n"
        f"Workflow: {hint}\n"
        f"DO NOT call jira_create_issue or acli directly.</important-reminder>",
        event_name="UserPromptSubmit",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run intent_detect tests**

```bash
python3 -m pytest hooks/tests/test_ai_hooks.py::TestIntentDetect -v
```

Expected: `5 passed`

---

### Task 2: Implement `ac_coverage.py`

**Files:**

- Create: `hooks/plugin/ai/ac_coverage.py`

Fires async after `post_hr9_alignment_suggest.py`. Scores semantic coverage % instead of just counting.

- [ ] **Step 1: Implement `ac_coverage.py`**

Create `hooks/plugin/ai/ac_coverage.py`:

```python
#!/usr/bin/env python3
"""PostToolUse async hook: semantic AC↔subtask coverage scoring.

Fires after jira_create_issue for subtasks. Calls claude -p to score
how well the subtask objectives semantically cover the parent story ACs.
Injects a warning if coverage score < 70%.

Exit code: 0 always.
"""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin
from hooks_state import _load, vs_get_coverage
from plugin.ai.claude_call import claude_call

_HOOK = "ai-ac-coverage"

_SCORE_PROMPT = """\
You are reviewing Jira subtask coverage of story acceptance criteria.

Story Acceptance Criteria:
{acs}

Subtask Objectives (created so far):
{subtasks}

Score (0-100): what percentage of the ACs are adequately addressed by the subtasks?
Consider semantic meaning, not just keyword matching.
Respond with only an integer 0-100."""


def check_coverage(acs: list[str], subtask_summaries: list[str]) -> Optional[int]:
    """Return coverage score 0-100, or None if unavailable."""
    if not acs or not subtask_summaries:
        return None

    acs_text = "\n".join(f"- {ac}" for ac in acs[:10])
    subtasks_text = "\n".join(f"- {s}" for s in subtask_summaries[:15])
    result = claude_call(_SCORE_PROMPT.format(acs=acs_text, subtasks=subtasks_text), timeout=12)

    if not result:
        return None
    try:
        return max(0, min(100, int(result.strip().split()[0])))
    except (ValueError, IndexError):
        return None


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    tool_input = data.get("tool_input", {})
    parent_key = None
    parent = tool_input.get("additional_fields", {})
    if isinstance(parent, str):
        try:
            parent = json.loads(parent)
        except json.JSONDecodeError:
            parent = {}
    if isinstance(parent, dict):
        p = parent.get("parent", {})
        parent_key = p.get("key") if isinstance(p, dict) else p

    if not parent_key:
        allow()
        return

    session_id = data.get("session_id", "")
    coverage = vs_get_coverage(session_id)
    acs = coverage["story_acs"].get(parent_key, [])

    # Collect subtask summaries from session state
    resp = data.get("tool_response", {})
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except json.JSONDecodeError:
            resp = {}
    new_summary = resp.get("fields", {}).get("summary", "") if isinstance(resp, dict) else ""

    state = _load(session_id)
    subtask_summaries = state.get("ai_subtask_summaries", {}).get(parent_key, [])
    if new_summary:
        subtask_summaries = subtask_summaries + [new_summary]
        # Persist updated list
        summaries_map = state.get("ai_subtask_summaries", {})
        summaries_map[parent_key] = subtask_summaries
        state["ai_subtask_summaries"] = summaries_map
        from hooks_state import _save
        _save(session_id, state)

    score = check_coverage(acs, subtask_summaries)
    if score is None:
        allow()
        return

    log_event(_HOOK, "SCORED", {"parent": parent_key, "score": score, "ac_count": len(acs)})

    if score < 70:
        inject_context(
            f"AI COVERAGE WARNING: {parent_key} — subtasks cover ~{score}% of ACs semantically. "
            f"{len(acs)} ACs tracked, {len(subtask_summaries)} subtask(s) so far. "
            f"Consider adding subtasks for uncovered ACs before running /verify-issue."
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run ac_coverage tests**

```bash
python3 -m pytest hooks/tests/test_ai_hooks.py::TestAcCoverage -v
```

Expected: `3 passed`

---

### Task 3: Implement `path_quality.py`

**Files:**

- Create: `hooks/plugin/ai/path_quality.py`

Fires async after Task agent completes. Rates if paths returned are specific enough.

- [ ] **Step 1: Implement `path_quality.py`**

Create `hooks/plugin/ai/path_quality.py`:

```python
#!/usr/bin/env python3
"""PostToolUse async hook: rate Explore agent path quality.

Fires after Task tool completes. If result contains file paths,
calls claude -p to rate specificity. Injects suggestion to re-explore
with more specific queries if rating is 'poor'.

Exit code: 0 always.
"""

import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import allow, inject_context, log_event, parse_stdin
from plugin.ai.claude_call import claude_call

_HOOK = "ai-path-quality"
_PATH_RE = re.compile(r"[`'\"]([a-zA-Z0-9_/.-]+\.[a-zA-Z]{1,5})[`'\"]")

_RATE_PROMPT = """\
Rate the specificity of these file paths for a software implementation task.
Good paths name specific files. Poor paths are just directories like src/ or lib/.

Paths:
{paths}

Respond with one word: good, fair, or poor."""


def extract_paths(text: str) -> list[str]:
    """Extract quoted file paths from text."""
    return list(dict.fromkeys(_PATH_RE.findall(text)))[:20]


def rate_paths(paths: list[str]) -> Optional[str]:
    """Return 'good', 'fair', 'poor', or None if unavailable."""
    if not paths:
        return None
    paths_text = "\n".join(f"- {p}" for p in paths[:15])
    result = claude_call(_RATE_PROMPT.format(paths=paths_text), timeout=10)
    if not result:
        return None
    rating = result.strip().lower().split()[0]
    return rating if rating in ("good", "fair", "poor") else None


def main() -> None:
    data = parse_stdin()
    if not data:
        allow()
        return

    if data.get("tool_name") != "Task":
        allow()
        return

    response = data.get("tool_response", "")
    if isinstance(response, dict):
        import json
        response = json.dumps(response)

    paths = extract_paths(str(response))
    if not paths:
        allow()
        return

    rating = rate_paths(paths)
    if rating is None:
        allow()
        return

    log_event(_HOOK, "RATED", {"rating": rating, "path_count": len(paths)})

    if rating == "poor":
        inject_context(
            f"AI PATH QUALITY: Explore returned {len(paths)} paths rated '{rating}'. "
            f"Paths like {paths[:3]} are too generic. Consider re-running Explore with "
            f"more specific queries (e.g. grep for class/function names, not just directories)."
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all AI hook tests**

```bash
python3 -m pytest hooks/tests/test_ai_hooks.py -v
```

Expected: `13 passed`

- [ ] **Step 3: Commit all three hooks**

```bash
git add hooks/plugin/ai/intent_detect.py hooks/plugin/ai/ac_coverage.py \
        hooks/plugin/ai/path_quality.py hooks/tests/test_ai_hooks.py
git commit -m "feat(ai): add LLM-powered intent_detect, ac_coverage, path_quality hooks"
```

---

### Task 4: Wire hooks into `hooks.json`

**Files:**

- Modify: `hooks/hooks.json`

- [ ] **Step 1: Add async UserPromptSubmit entry for intent_detect**

In `hooks.json`, find the `"UserPromptSubmit"` section and add after the existing entries:

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/ai/intent_detect.py",
  "async": true
}
```

- [ ] **Step 2: Add async PostToolUse entry for ac_coverage**

In the `"PostToolUse"` section, find the matcher for `mcp__mcp-atlassian__jira_create_issue` and add a new entry after the existing hooks for that matcher:

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/ai/ac_coverage.py",
  "async": true
}
```

- [ ] **Step 3: Add async PostToolUse entry for path_quality**

In the `"PostToolUse"` section, find the `"matcher": "Task"` entry and add after existing hooks:

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh\" hooks/plugin/ai/path_quality.py",
  "async": true
}
```

- [ ] **Step 4: Validate hooks.json is valid JSON**

```bash
python3 -c "import json; json.load(open('hooks/hooks.json')); print('Valid JSON')"
```

Expected: `Valid JSON`

- [ ] **Step 5: Smoke test — trigger UserPromptSubmit hook manually**

```bash
echo '{"prompt": "สร้าง bug สำหรับ login ไม่ได้", "session_id": "test123", "hook_event_name": "UserPromptSubmit"}' \
  | python3 hooks/plugin/ai/intent_detect.py
```

Expected: JSON output with `additionalContext` containing `AI INTENT CONFIRMED — BUG`

- [ ] **Step 6: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat(ai): wire AI hooks into hooks.json as async entries (Phase 2)"
```

---

## Phase 2 Complete

Three async AI hooks are live. They fire alongside existing sync hooks — no regressions possible since all exit 0 and are `async: true`.
