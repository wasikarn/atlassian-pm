#!/usr/bin/env python3
"""Workflow state checkpoint CLI.

Tracks workflow phase progress and enforces prerequisites.
State persists in tasks/.workflow-state.json.

Usage:
    # Start a workflow
    python workflow_checkpoint.py start story-full BEP-1200

    # Record quality gate pass
    python workflow_checkpoint.py pass-gate qg-story 94.5

    # Advance to next phase
    python workflow_checkpoint.py advance create-story

    # Check prerequisite
    python workflow_checkpoint.py check qg-story

    # Show current status
    python workflow_checkpoint.py status

    # Complete workflow
    python workflow_checkpoint.py complete

Exit codes:
    0 = success / prerequisite met
    1 = prerequisite NOT met / error
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.workflow_state import WorkflowState

# State directory
TASKS_DIR = Path(__file__).parent.parent.parent.parent.parent / "tasks"


def cmd_start(args: argparse.Namespace) -> int:
    """Start a new workflow."""
    ws = WorkflowState(args.workflow, args.context_key, TASKS_DIR)
    ws.start()
    print(f"\u2705 Started: {args.workflow} ({args.context_key})")
    return 0


def cmd_pass_gate(args: argparse.Namespace) -> int:
    """Record quality gate pass."""
    ws = WorkflowState(args.workflow, args.context_key, TASKS_DIR)
    score = float(args.score)
    ws.pass_gate(args.gate, score)
    icon = "\u2705" if score >= 90 else "\u26a0\ufe0f"
    print(f"{icon} Gate '{args.gate}': {score:.1f}%")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    """Advance to next phase."""
    ws = WorkflowState(args.workflow, args.context_key, TASKS_DIR)
    ws.advance(args.phase)
    print(f"\u2705 Advanced: {args.phase}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check if prerequisite is met."""
    ws = WorkflowState(args.workflow, args.context_key, TASKS_DIR)
    met = ws.check(args.prerequisite)
    if met:
        print(f"\u2705 Prerequisite '{args.prerequisite}' met")
        return 0
    else:
        print(f"\u274c Prerequisite '{args.prerequisite}' NOT met")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Show workflow status."""
    if args.all:
        active = WorkflowState.get_all_active(TASKS_DIR)
        if not active:
            print("No active workflows")
            return 0
        for entry in active:
            key = entry.pop("_key", "?")
            status = entry.get("status", "?")
            phases = entry.get("phases_completed", [])
            gates = entry.get("gates_passed", {})
            print(f"  {key}: {status} | phases: {len(phases)} | gates: {len(gates)}")
        return 0

    ws = WorkflowState(args.workflow, args.context_key, TASKS_DIR)
    state = ws.to_dict()

    if args.json:
        print(json.dumps(state, indent=2))
    else:
        if not state:
            print(f"No active workflow: {args.workflow} ({args.context_key})")
            return 1
        print(f"Workflow: {state.get('workflow', '?')}")
        print(f"Context: {state.get('context_key', '?')}")
        print(f"Status: {state.get('status', '?')}")
        print(f"Current Phase: {state.get('current_phase', 'none')}")
        gates = state.get("gates_passed", {})
        if gates:
            print("Gates Passed:")
            for gate, info in gates.items():
                print(f"  \u2705 {gate}: {info['score']:.1f}%")
        phases = state.get("phases_completed", [])
        if phases:
            phases_str = " → ".join(phases)
            print(f"Phases: {phases_str}")

    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    """Complete workflow."""
    ws = WorkflowState(args.workflow, args.context_key, TASKS_DIR)
    ws.complete()
    print(f"\u2705 Completed: {args.workflow} ({args.context_key})")
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Remove stale entries."""
    removed = WorkflowState.clear_stale(TASKS_DIR)
    print(f"Removed {removed} stale entries")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Workflow state checkpoint (phase tracking + prerequisite enforcement)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Common args for workflow identification
    def add_workflow_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("workflow", help="Workflow name (e.g., story-full)")
        p.add_argument("context_key", help="Context key (e.g., BEP-1200)")

    # start
    p = subparsers.add_parser("start", help="Start new workflow")
    add_workflow_args(p)

    # pass-gate
    p = subparsers.add_parser("pass-gate", help="Record quality gate pass")
    add_workflow_args(p)
    p.add_argument("gate", help="Gate name (e.g., qg-story)")
    p.add_argument("score", help="Gate score (0-100)")

    # advance
    p = subparsers.add_parser("advance", help="Advance to next phase")
    add_workflow_args(p)
    p.add_argument("phase", help="Phase name (e.g., create-story)")

    # check
    p = subparsers.add_parser("check", help="Check prerequisite")
    add_workflow_args(p)
    p.add_argument("prerequisite", help="Prerequisite gate or phase name")

    # status
    p = subparsers.add_parser("status", help="Show workflow status")
    p.add_argument("workflow", nargs="?", help="Workflow name")
    p.add_argument("context_key", nargs="?", help="Context key")
    p.add_argument("--all", action="store_true", help="Show all active workflows")
    p.add_argument("--json", action="store_true", help="JSON output")

    # complete
    p = subparsers.add_parser("complete", help="Complete workflow")
    add_workflow_args(p)

    # cleanup
    subparsers.add_parser("cleanup", help="Remove stale entries")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "start": cmd_start,
        "pass-gate": cmd_pass_gate,
        "advance": cmd_advance,
        "check": cmd_check,
        "status": cmd_status,
        "complete": cmd_complete,
        "cleanup": cmd_cleanup,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
