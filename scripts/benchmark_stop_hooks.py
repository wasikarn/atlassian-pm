#!/usr/bin/env python3
"""Benchmark stop hooks performance after optimization.

Tests the actual stop hooks with and without state to measure improvement.
"""
import time
import subprocess
import json
import os
import statistics
import tempfile
from pathlib import Path

def run_stop_hook(hook_path: str, session_id: str = None) -> tuple[float, dict]:
    """Run a stop hook and return execution time + result."""
    env = os.environ.copy()
    env["ATLASSIAN_PM_INTERNAL"] = "true"

    stdin_data = json.dumps({"session_id": session_id}) if session_id else ""

    start = time.perf_counter()
    result = subprocess.run(
        ["python3", hook_path],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=10,
        env=env
    )
    elapsed = (time.perf_counter() - start) * 1000  # ms

    try:
        output = json.loads(result.stdout) if result.stdout else {"ok": True}
    except json.JSONDecodeError:
        output = {"error": result.stdout, "stderr": result.stderr}

    return elapsed, output, result.returncode

def benchmark_no_state():
    """Benchmark when no state DB exists (fast path)."""
    print("=" * 60)
    print("Test 1: No state DB (fast path exit)")
    print("=" * 60)

    hooks = [
        ("HR6 Unflushed Check", "hooks/plugin/guards/stop_hr6_unflushed_check.py"),
        ("HR5 Pending Check", "hooks/plugin/session/stop_hr5_pending_check.py"),
    ]

    for name, hook_path in hooks:
        times = []
        for i in range(10):
            elapsed, output, code = run_stop_hook(hook_path, "test_no_state_" + str(i))
            times.append(elapsed)

        avg = statistics.mean(times)
        min_t = min(times)
        max_t = max(times)

        print(f"\n{name}:")
        print(f"  Avg: {avg:.2f}ms | Min: {min_t:.2f}ms | Max: {max_t:.2f}ms")
        print(f"  {'PASS' if avg < 50 else 'FAIL'} (target < 50ms for fast path)")

def benchmark_with_empty_state():
    """Benchmark when state DB exists but no pending items."""
    print("\n" + "=" * 60)
    print("Test 2: Empty state DB (connection + query)")
    print("=" * 60)

    import sys
    sys.path.insert(0, "hooks")
    from hooks_state import _get_connection, hr6_add_pending, hr6_clear_all_pending, hr5_add_pending, STATE_DIR

    session_id = "benchmark_empty_state"

    # Create empty state DB
    conn = _get_connection(session_id)
    conn.close()

    try:
        hooks = [
            ("HR6 Unflushed Check", "hooks/plugin/guards/stop_hr6_unflushed_check.py"),
            ("HR5 Pending Check", "hooks/plugin/session/stop_hr5_pending_check.py"),
        ]

        for name, hook_path in hooks:
            times = []
            for _ in range(10):
                elapsed, output, code = run_stop_hook(hook_path, session_id)
                times.append(elapsed)

            avg = statistics.mean(times)
            min_t = min(times)
            max_t = max(times)

            print(f"\n{name}:")
            print(f"  Avg: {avg:.2f}ms | Min: {min_t:.2f}ms | Max: {max_t:.2f}ms")
            print(f"  {'PASS' if avg < 100 else 'FAIL'} (target < 100ms with empty state)")

    finally:
        # Cleanup
        db_path = STATE_DIR / f"{session_id}.db"
        if db_path.exists():
            db_path.unlink()

def benchmark_with_pending():
    """Benchmark when there are pending items."""
    print("\n" + "=" * 60)
    print("Test 3: State with pending items (full check)")
    print("=" * 60)

    import sys
    sys.path.insert(0, "hooks")
    from hooks_state import hr6_add_pending, hr6_clear_all_pending, hr5_add_pending, STATE_DIR

    session_id = "benchmark_with_pending"

    # Create state with pending items
    hr6_add_pending(session_id, "TEST-123")
    hr6_add_pending(session_id, "TEST-456")
    hr5_add_pending(session_id, "TEST-789", "PARENT-1")

    try:
        elapsed, output, code = run_stop_hook(
            "hooks/plugin/guards/stop_hr6_unflushed_check.py",
            session_id
        )
        print(f"\nHR6 with pending items:")
        print(f"  Time: {elapsed:.2f}ms")
        print(f"  Output: {output}")
        print(f"  {'PASS' if elapsed < 100 else 'FAIL'} (target < 100ms)")

        elapsed, output, code = run_stop_hook(
            "hooks/plugin/session/stop_hr5_pending_check.py",
            session_id
        )
        print(f"\nHR5 with pending items:")
        print(f"  Time: {elapsed:.2f}ms")
        print(f"  Output: {output}")
        print(f"  {'PASS' if elapsed < 100 else 'FAIL'} (target < 100ms)")

    finally:
        # Cleanup
        hr6_clear_all_pending(session_id)
        db_path = STATE_DIR / f"{session_id}.db"
        if db_path.exists():
            db_path.unlink()

def benchmark_pgrep_comparison():
    """Compare old pgrep vs new lock file check."""
    print("\n" + "=" * 60)
    print("Test 4: pgrep vs lock file check performance")
    print("=" * 60)

    # Old method: pgrep -f
    times_old = []
    for _ in range(10):
        start = time.perf_counter()
        subprocess.run(
            ["pgrep", "-f", "atlassian-cache/server.py"],
            capture_output=True,
            timeout=5
        )
        times_old.append((time.perf_counter() - start) * 1000)

    # New method: check file existence
    times_new = []
    for _ in range(10):
        start = time.perf_counter()
        Path("/tmp/atlassian-cache.pid").exists()
        times_new.append((time.perf_counter() - start) * 1000)

    print(f"\nOld (pgrep -f):")
    print(f"  Avg: {statistics.mean(times_old):.2f}ms | Max: {max(times_old):.2f}ms")

    print(f"\nNew (lock file check):")
    print(f"  Avg: {statistics.mean(times_new):.4f}ms | Max: {max(times_new):.4f}ms")

    speedup = statistics.mean(times_old) / statistics.mean(times_new)
    print(f"\nSpeedup: {speedup:.0f}x")

if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])

    print("Stop Hooks Performance Benchmark")
    print("=" * 60)
    print(f"Python: {subprocess.check_output(['python3', '--version'], text=True).strip()}")
    print(f"Platform: {os.uname().sysname} {os.uname().machine}")
    print()

    benchmark_no_state()
    benchmark_with_empty_state()
    benchmark_with_pending()
    benchmark_pgrep_comparison()

    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)
