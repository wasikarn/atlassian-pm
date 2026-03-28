"""JSON parsing utilities: markdown fence stripping + schema validation.

# Shared with: scripts/ai/json_utils.py, monitor/json_utils.py
# Each copy carries its own schemas — keep strip_fences / parse_json in sync.

Stdlib only. No third-party dependencies.
"""

import json
import re

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n\s*```\s*$", flags=re.DOTALL)


def strip_fences(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences from LLM response."""
    m = _FENCE_RE.match(text.strip())
    return m.group(1) if m else text


def parse_json(text: str, schema: dict | None = None) -> dict | None:
    """Parse JSON string with fence stripping and optional schema validation.

    Schema format (stdlib-only):
        {
            "key": {
                "type": <type>,        # required — e.g. str, int, bool, list
                "required": True,      # optional — default False
                "choices": [...],      # optional — valid values (lowercased for str)
                "min": <number>,       # optional — clamp int/float to this minimum
                "max": <number>,       # optional — clamp int/float to this maximum
            }
        }

    Returns:
        dict on success, None on any parse or validation failure.
    """
    try:
        data = json.loads(strip_fences(text.strip()))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    if not schema:
        return data
    for key, rules in schema.items():
        if rules.get("required") and key not in data:
            return None
        if key not in data:
            continue
        val = data[key]
        expected = rules["type"]
        # bool is a subclass of int in Python — check bool before int
        if expected is int and isinstance(val, bool):
            return None
        if not isinstance(val, expected):
            return None
        if "choices" in rules:
            if isinstance(val, str):
                val = val.lower()
                data[key] = val
            if val not in rules["choices"]:
                return None
        if "min" in rules and val < rules["min"]:
            data[key] = rules["min"]
        if "max" in rules and val > rules["max"]:
            data[key] = rules["max"]
    return data


# ── Python schemas (for parse_json fallback) ──────────────────────────────────

SCORE_SCHEMA: dict = {
    "score": {"type": int, "required": True, "min": 0, "max": 100},
}

CLASSIFY_SCHEMA: dict = {
    "intent": {
        "type": str,
        "required": True,
        "choices": ["bug", "story", "epic", "subtask", "task", "none"],
    },
}

RATE_SCHEMA: dict = {
    "rating": {"type": str, "required": True, "choices": ["good", "fair", "poor"]},
    "suggestion": {"type": str, "required": False},
}

# ── JSON Schemas (for --json-schema flag → structured_output) ─────────────────

SCORE_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 100}},
    "required": ["score"],
}

CLASSIFY_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["bug", "story", "epic", "subtask", "task", "none"],
        }
    },
    "required": ["intent"],
}

RATE_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "rating": {"type": "string", "enum": ["good", "fair", "poor"]},
        "suggestion": {"type": "string"},
    },
    "required": ["rating"],
}

# ── JSON Schemas (for --json-schema flag → structured_output) ─────────────────

SCORE_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 100}},
    "required": ["score"],
}

CLASSIFY_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["bug", "story", "epic", "subtask", "task", "none"],
        }
    },
    "required": ["intent"],
}

RATE_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "rating": {"type": "string", "enum": ["good", "fair", "poor"]}
    },
    "required": ["rating"],
}
