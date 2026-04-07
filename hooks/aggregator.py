#!/usr/bin/env python3
"""
Hook aggregation framework for atlassian-pm.

Runs multiple hook scripts in a single Python process, eliminating
subprocess startup overhead (~28ms per avoided subprocess).
"""
import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import NamedTuple


class _HookResult(NamedTuple):
    exit_code: int
    stdout: str
    stderr: str


def _run_hook(hook_path: Path, stdin_data: str) -> _HookResult:
    """Load and run one hook script, capturing all output.

    Handles both script patterns:
    - Pattern A: has main() called at __name__ == '__main__'
    - Pattern B: top-level logic with direct sys.exit() calls
    """

    class _Done(BaseException):
        def __init__(self, code: int = 0):
            self.code = int(code) if code is not None else 0

    captured_out = io.StringIO()
    captured_err = io.StringIO()

    orig_stdin = sys.stdin
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    orig_exit = sys.exit

    sys.stdin = io.StringIO(stdin_data)
    sys.stdout = captured_out
    sys.stderr = captured_err

    def patched_exit(code=0):
        raise _Done(code)

    sys.exit = patched_exit

    exit_code: int | None = None
    mod = None

    try:
        spec = importlib.util.spec_from_file_location(
            f"_agg_{hook_path.stem}", hook_path
        )
        if spec is None:
            return _HookResult(0, "", "")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        # exec_module completed: Pattern A (main() not yet called)
    except _Done as e:
        exit_code = e.code  # Pattern B: top-level logic exited
    except Exception:
        exit_code = 2
    finally:
        # Restore everything (will be re-patched for main() call if needed)
        sys.stdin = orig_stdin
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        sys.exit = orig_exit

    # Pattern A: call main() in a fresh patched context
    if exit_code is None and mod is not None and hasattr(mod, "main"):
        captured_out2 = io.StringIO()
        captured_err2 = io.StringIO()

        sys.stdin = io.StringIO(stdin_data)
        sys.stdout = captured_out2
        sys.stderr = captured_err2
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

        # Merge output from exec_module + main() phases
        captured_out = io.StringIO(captured_out.getvalue() + captured_out2.getvalue())
        captured_err = io.StringIO(captured_err.getvalue() + captured_err2.getvalue())

    return _HookResult(
        exit_code=exit_code if exit_code is not None else 0,
        stdout=captured_out.getvalue(),
        stderr=captured_err.getvalue(),
    )


def _extract_contexts(stdout: str) -> list[str]:
    """Parse inject_context JSON objects from hook stdout (one per line)."""
    contexts: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            ctx = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
            if ctx:
                contexts.append(ctx)
        except (json.JSONDecodeError, AttributeError):
            pass
    return contexts


def run(hook_paths: list[str | Path], event_name: str = "PostToolUse") -> None:
    """Run hooks sequentially in a single process.

    Args:
        hook_paths: Absolute paths to hook scripts (sync only — no async hooks).
        event_name: Hook event name for merged inject_context output.
    """
    stdin_data = sys.stdin.read()
    all_contexts: list[str] = []

    for path in hook_paths:
        p = Path(path)
        if not p.exists():
            continue

        result = _run_hook(p, stdin_data)

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
