#!/usr/bin/env python3
import time
import subprocess
import json
import os
import statistics
from pathlib import Path

def benchmark_stop_hooks():
    print("🚀 Starting Stop-Hooks Performance Benchmark...")

    # Simulation: we trigger the stop hooks via a mock environment
    # In a real scenario, this would be the 'running stop hooks' phase of Claude Code

    results = []
    iterations = 10

    # We simulate the execution of the two main stop hooks
    hooks = [
        "hooks/plugin/guards/stop_hr6_unflushed_check.py",
        "hooks/plugin/session/stop_hr5_pending_check.py"
    ]

    # Mock session ID
    session_id = "bench_session_123"
    os.environ["session_id"] = session_id
    os.environ["ATLASSIAN_PM_INTERNAL"] = "true"

    for i in range(iterations):
        start_time = time.perf_counter()

        for hook in hooks:
            subprocess.run(["python3", f"hooks/{hook}"], input='{"session_id": "{session_id}"}', text=True, capture_output=True)

        end_time = time.perf_counter()
        results.append((end_time - start_time) * 1000) # ms

    avg_time = statistics.mean(results)
    min_time = min(results)
    max_time = max(results)

    print(f"\n--- Results ---")
    print(f"Iterations: {iterations}")
    print(f"Average execution time: {avg_time:.2f} ms")
    print(f"Minimum execution time: {min_time:.2f} ms")
    print(f"Maximum execution time: {max_time:.2f} ms")
    print(f"Conclusion: {'PASS' if avg_time < 100 else 'FAIL'} (Target < 100ms)")

if __name__ == "__main__":
    benchmark_stop_hooks()
