#!/usr/bin/env python3
"""Aggregated: SubagentStart hooks — 2 hooks in 1 subprocess.

Replaces separate subprocess calls to:
  - session/start_subagent_context.py
  - session/start_intelligence_inject.py --subagent

The second hook requires sys.argv patching to receive --subagent flag.

Saves ~28ms (1 avoided subprocess startup × 28ms).
"""
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from typing import NamedTuple


class _HookResult(NamedTuple):
    exit_code: int
    stdout: str
    stderr: str


PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from aggregator import _extract_contexts, _run_hook

HOOK1 = PLUGIN_ROOT / "hooks/plugin/session/start_subagent_context.py"
HOOK2 = PLUGIN_ROOT / "hooks/plugin/session/start_intelligence_inject.py"


def _run_hook_with_argv(hook_path: Path, stdin_data: str, argv: list[str]) -> _HookResult:
    """Run hook with custom sys.argv (for hooks that use argparse)."""

    class _Done(BaseException):
        def __init__(self, code: int = 0):
            self.code = int(code) if code is not None else 0

    captured_out = io.StringIO()
    captured_err = io.StringIO()

    orig_stdin = sys.stdin
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    orig_exit = sys.exit
    orig_argv = sys.argv

    sys.stdin = io.StringIO(stdin_data)
    sys.stdout = captured_out
    sys.stderr = captured_err
    sys.argv = argv

    def patched_exit(code=0):
        raise _Done(code)

    sys.exit = patched_exit

    exit_code: int | None = None
    mod = None

    try:
        spec = importlib.util.spec_from_file_location(
            f"_agg_{hook_path.stem}", hook_path
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except _Done as e:
        exit_code = e.code
    except Exception:
        exit_code = 2
    finally:
        sys.stdin = orig_stdin
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        sys.exit = orig_exit
        sys.argv = orig_argv

    # Pattern A: call main() in a fresh patched context
    if exit_code is None and mod is not None and hasattr(mod, "main"):
        captured_out2 = io.StringIO()
        captured_err2 = io.StringIO()

        sys.stdin = io.StringIO(stdin_data)
        sys.stdout = captured_out2
        sys.stderr = captured_err2
        sys.argv = argv
        sys.exit = patched_exit

        try:
            mod.main()
            exit_code = 0
        except _Done as e:
            exit_code = e.code
        except Exception:
            exit_code = 2
        finally:
            sys.stdin = orig_stdin
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            sys.exit = orig_exit
            sys.argv = orig_argv

        captured_out = io.StringIO(captured_out.getvalue() + captured_out2.getvalue())
        captured_err = io.StringIO(captured_err.getvalue() + captured_err2.getvalue())

    return _HookResult(
        exit_code=exit_code if exit_code is not None else 0,
        stdout=captured_out.getvalue(),
        stderr=captured_err.getvalue(),
    )


def run(hook_paths: list[tuple[str | Path, list[str]]], event_name: str = "SubagentStart") -> None:
    """Run hooks sequentially with custom argv support.

    Args:
        hook_paths: List of (path, argv) tuples.
        event_name: Hook event name for merged inject_context output.
    """
    stdin_data = sys.stdin.read()
    all_contexts: list[str] = []

    for path, argv in hook_paths:
        p = Path(path)
        if not p.exists():
            continue

        result = _run_hook_with_argv(p, stdin_data, argv)

        if result.exit_code != 0:
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            sys.exit(result.exit_code)

        all_contexts.extend(_extract_contexts(result.stdout))

    if all_contexts:
        merged = "\n\n---\n\n".join(all_contexts)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": merged,
            }
        }))

    sys.exit(0)


if __name__ == "__main__":
    run([
        (HOOK1, ["start_subagent_context.py"]),
        (HOOK2, ["start_intelligence_inject.py", "--subagent"]),
    ], event_name="SubagentStart")
