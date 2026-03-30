"""UserPromptSubmit hook: warn when context window is approaching capacity.

Estimates context density from conversation transcript length and warns
at 70% / 90% thresholds to prevent mid-workflow context exhaustion.

Advisory only — never blocks the user prompt.
Exit 0 = always allow.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import inject_context, parse_stdin

# Claude Code default: 200K tokens ≈ 800K chars (Sonnet context window in plugin mode)
# Warn at 70% ≈ 560K chars, urgent at 90% ≈ 720K chars
# Skip warning below 100K chars (normal early-session size)
_SKIP_BELOW_CHARS  =  100_000
_WARN_CHARS        =  560_000   # ~70% of 200K token window
_URGENT_CHARS      =  720_000   # ~90% of 200K token window

# Also warn based on turn count (proxy for accumulated tool output)
_WARN_TURNS   = 30   # ~30 user messages = substantial context
_URGENT_TURNS = 50   # ~50 user messages = critical


def _estimate_transcript(transcript: list) -> tuple[int, int]:
    """Return (char_count, user_turn_count) from transcript."""
    chars = 0
    turns = 0
    for msg in transcript:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        if role == "user":
            turns += 1
        # Estimate chars from content
        content = msg.get("content", "")
        if isinstance(content, str):
            chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    chars += len(str(block.get("text", "") or block.get("content", "")))
    return chars, turns


def main() -> None:
    data = parse_stdin()
    if not data:
        sys.exit(0)

    transcript = data.get("transcript", [])
    if not transcript:
        sys.exit(0)

    try:
        chars, turns = _estimate_transcript(transcript)
    except Exception:
        sys.exit(0)

    if chars < _SKIP_BELOW_CHARS and turns < _WARN_TURNS:
        sys.exit(0)

    is_urgent = chars >= _URGENT_CHARS or turns >= _URGENT_TURNS
    is_warn   = chars >= _WARN_CHARS   or turns >= _WARN_TURNS

    if is_urgent:
        inject_context(
            f"⚠️ CONTEXT CRITICAL (~{chars // 1000}K chars, {turns} turns). "
            "Run /compact NOW to prevent mid-workflow exhaustion. "
            "Preserve: issue keys created, sprint IDs, active skill phase, pending HR5/HR6 ops.",
            event_name="UserPromptSubmit",
        )
    elif is_warn:
        inject_context(
            f"⚡ Context large (~{chars // 1000}K chars, {turns} turns). "
            "Consider /compact before starting a new skill. "
            "Preserve on compact: issue keys, sprint IDs, QG scores, active phase.",
            event_name="UserPromptSubmit",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
