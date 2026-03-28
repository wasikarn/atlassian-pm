#!/usr/bin/env python3
"""StopHook: log AI session cost summary."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from hooks_state import load_state
    state = load_state()
    cost = state.get("session_ai_cost_usd", 0.0)
    calls = state.get("session_ai_calls", 0)
    if calls > 0:
        # Inject into context so user sees it
        from hooks_lib import inject_context
        inject_context(
            f"Session AI usage: {calls} call{'s' if calls != 1 else ''} · "
            f"${cost:.4f} total cost",
            event_name="Stop",
        )
except Exception:
    pass  # Never fail the session stop
