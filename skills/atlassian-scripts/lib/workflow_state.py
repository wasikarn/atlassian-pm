"""Workflow state management for skill phase tracking.

Tracks workflow progress through phases, enforces prerequisites,
and auto-clears stale state after TTL.

State persists in tasks/.workflow-state.json.

Usage:
    from lib.workflow_state import WorkflowState

    ws = WorkflowState("story-full", "BEP-1200")
    ws.start()
    ws.pass_gate("qg-story", 94.5)
    ws.advance("create-story")
    ws.check("qg-story")  # True
    ws.complete()
"""

import json
import time
from pathlib import Path
from typing import Any

# Default state file location
DEFAULT_STATE_DIR = Path(__file__).parent.parent.parent.parent.parent / "tasks"
STATE_FILE_NAME = ".workflow-state.json"
STATE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


class WorkflowState:
    """Track workflow phase progress with prerequisite enforcement.

    Attributes:
        workflow: Workflow name (e.g., "story-full")
        context_key: Issue key or identifier (e.g., "BEP-1200")
        state_dir: Directory for state file
    """

    def __init__(
        self,
        workflow: str,
        context_key: str,
        state_dir: Path | None = None,
    ) -> None:
        self.workflow = workflow
        self.context_key = context_key
        self.state_dir = state_dir or DEFAULT_STATE_DIR
        self.state_file = self.state_dir / STATE_FILE_NAME
        self._state: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Load state from file, auto-clearing stale entries."""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file) as f:
                all_state = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

        # Auto-clear stale entries
        now = time.time()
        cleaned = {}
        for key, entry in all_state.items():
            if now - entry.get("updated_at", 0) < STATE_TTL_SECONDS:
                cleaned[key] = entry

        # Get current workflow state
        state_key = f"{self.workflow}:{self.context_key}"
        return cleaned.get(state_key, {})

    def _save(self) -> None:
        """Save state to file."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load all state (to preserve other workflows)
        all_state = {}
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    all_state = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        state_key = f"{self.workflow}:{self.context_key}"
        self._state["updated_at"] = time.time()
        all_state[state_key] = self._state

        with open(self.state_file, "w") as f:
            json.dump(all_state, f, indent=2)

    def start(self) -> None:
        """Start a new workflow, clearing any previous state."""
        self._state = {
            "workflow": self.workflow,
            "context_key": self.context_key,
            "status": "in_progress",
            "current_phase": None,
            "gates_passed": {},
            "phases_completed": [],
            "started_at": time.time(),
            "updated_at": time.time(),
        }
        self._save()

    def pass_gate(self, gate_name: str, score: float) -> None:
        """Record a quality gate pass.

        Args:
            gate_name: Gate identifier (e.g., "qg-story", "qg-subtask")
            score: Quality gate score (0-100)
        """
        gates = self._state.setdefault("gates_passed", {})
        gates[gate_name] = {
            "score": score,
            "passed_at": time.time(),
        }
        self._save()

    def advance(self, phase_name: str) -> None:
        """Mark a phase as completed and advance to next.

        Args:
            phase_name: Phase identifier (e.g., "create-story", "explore")
        """
        completed = self._state.setdefault("phases_completed", [])
        if phase_name not in completed:
            completed.append(phase_name)
        self._state["current_phase"] = phase_name
        self._save()

    def check(self, prerequisite: str) -> bool:
        """Check if a prerequisite gate or phase has been completed.

        Args:
            prerequisite: Gate or phase name to check

        Returns:
            True if prerequisite is met.
        """
        gates = self._state.get("gates_passed", {})
        phases = self._state.get("phases_completed", [])
        return prerequisite in gates or prerequisite in phases

    def complete(self) -> None:
        """Mark workflow as completed."""
        self._state["status"] = "completed"
        self._state["completed_at"] = time.time()
        self._save()

    def to_dict(self) -> dict[str, Any]:
        """Return current state as dict."""
        return dict(self._state)

    @classmethod
    def get_all_active(cls, state_dir: Path | None = None) -> list[dict[str, Any]]:
        """Get all active (non-stale) workflow states."""
        state_dir = state_dir or DEFAULT_STATE_DIR
        state_file = state_dir / STATE_FILE_NAME

        if not state_file.exists():
            return []

        try:
            with open(state_file) as f:
                all_state = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        now = time.time()
        active = []
        for key, entry in all_state.items():
            if now - entry.get("updated_at", 0) < STATE_TTL_SECONDS:
                entry["_key"] = key
                active.append(entry)

        return active

    @classmethod
    def clear_stale(cls, state_dir: Path | None = None) -> int:
        """Remove stale entries. Returns count removed."""
        state_dir = state_dir or DEFAULT_STATE_DIR
        state_file = state_dir / STATE_FILE_NAME

        if not state_file.exists():
            return 0

        try:
            with open(state_file) as f:
                all_state = json.load(f)
        except (json.JSONDecodeError, OSError):
            return 0

        now = time.time()
        original_count = len(all_state)
        cleaned = {k: v for k, v in all_state.items() if now - v.get("updated_at", 0) < STATE_TTL_SECONDS}

        removed = original_count - len(cleaned)
        if removed > 0:
            with open(state_file, "w") as f:
                json.dump(cleaned, f, indent=2)

        return removed
