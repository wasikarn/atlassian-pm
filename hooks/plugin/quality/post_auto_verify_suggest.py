"""PostToolUse hook: after successful `acli --from-json`, suggest /verify-issue.

Parses the acli output for issue keys and suggests verification.
Exit 0 = allow (always), injects additionalContext suggestion.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hooks_lib import inject_context, parse_stdin

data = parse_stdin()
if not data:
    sys.exit(0)

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
# PostToolUse provides tool_response; fall back to tool_output for compatibility
tool_response = str(data.get("tool_response", "") or data.get("tool_output", ""))

if tool_name != "Bash":
    sys.exit(0)

command = tool_input.get("command", "")
if "--from-json" not in command:
    sys.exit(0)

if not tool_response or "error" in tool_response.lower():
    sys.exit(0)

# Extract issue keys from output or command
keys = re.findall(r"[A-Z]+-\d+", tool_response)
if not keys:
    keys = re.findall(r"[A-Z]+-\d+", command.upper())

if keys:
    unique_keys = list(dict.fromkeys(keys))  # deduplicate preserving order
    msg = f"Issue updated successfully. Consider: `/verify-issue {unique_keys[0]}`"
    if len(unique_keys) > 1:
        msg += f"\n   All keys: {', '.join(unique_keys[:5])}"
    inject_context(msg)

sys.exit(0)
