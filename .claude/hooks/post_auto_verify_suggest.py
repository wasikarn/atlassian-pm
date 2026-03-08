#!/usr/bin/env python3
"""PostToolUse hook: after successful `acli --from-json`, suggest /verify-issue.

Parses the acli output for issue keys and suggests verification.
Exit 0 = allow (always), prints additionalContext suggestion.
"""

import json
import re
import sys

raw = sys.stdin.read()
data = json.loads(raw)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
tool_output = data.get("tool_output", "")

# Only trigger on Bash calls with acli --from-json
if tool_name != "Bash":
    sys.exit(0)

command = tool_input.get("command", "")
if "--from-json" not in command:
    sys.exit(0)

# Check for success indicators (acli outputs the key on success)
if not tool_output or "error" in tool_output.lower():
    sys.exit(0)

# Extract issue keys from output or command
keys = re.findall(r"[A-Z]+-\d+", tool_output)
if not keys:
    # Try extracting from the JSON filename pattern (e.g., tasks/bep-123-update.json)
    keys = re.findall(r"[A-Z]+-\d+", command.upper())

if keys:
    unique_keys = list(dict.fromkeys(keys))  # deduplicate preserving order
    key_list = ", ".join(unique_keys[:5])  # limit to 5 keys
    print(f"💡 Issue updated successfully. Consider: `/verify-issue {unique_keys[0]}`")
    if len(unique_keys) > 1:
        print(f"   All keys: {key_list}")

sys.exit(0)
