#!/usr/bin/env python3
"""Run multiple AI scripts in parallel via Popen.

Usage:
    from scripts.ai.parallel_runner import run_parallel

    results = run_parallel([
        ("polish", ["python3", "scripts/ai/pre_qg_polish.py", "--stdin", "--type", "story"]),
        ("suggest", ["python3", "scripts/ai/suggest_subtasks.py", "--story", "TP-123", "--acs", acs_text]),
    ], timeout=35)
    polished_adf = results.get("polish")   # stdout string or None
    subtasks     = results.get("suggest")  # stdout string or None

Each process receives its own recursion guard via inherited environment.
Caller is responsible for any subprocess that reads stdin (pass input= if needed).
"""

import subprocess


def run_parallel(
    scripts: list[tuple[str, list[str]]],
    timeout: int = 35,
    inputs: dict[str, str] | None = None,
) -> dict[str, str | None]:
    """Launch scripts concurrently, return {name: stdout | None}.

    Args:
        scripts:  List of (name, cmd) pairs. cmd is the argv list.
        timeout:  Per-process communicate() timeout in seconds.
        inputs:   Optional {name: stdin_text} for processes that read stdin.

    Returns:
        Dict mapping name → stdout string (stripped) on success, None on any error.
    """
    procs: dict[str, subprocess.Popen[str]] = {}
    for name, cmd in scripts:
        stdin_data = (inputs or {}).get(name)
        procs[name] = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if stdin_data is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    results: dict[str, str | None] = {}
    for name, proc in procs.items():
        stdin_data = (inputs or {}).get(name)
        try:
            stdout, _ = proc.communicate(input=stdin_data, timeout=timeout)
            results[name] = stdout.strip() if proc.returncode == 0 and stdout.strip() else None
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            results[name] = None
        except Exception:
            results[name] = None

    return results
