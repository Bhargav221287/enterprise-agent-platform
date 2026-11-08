#!/usr/bin/env python3
"""Test runner script to execute orchestrator and verifier test suites cleanly."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_tests():
    print("=" * 60)
    print("Running Orchestrator Test Suite...")
    print("=" * 60)
    res1 = subprocess.run(
        [sys.executable, "-m", "pytest", "orchestrator/tests", "-v"],
        cwd=REPO_ROOT,
    )

    print("\n" + "=" * 60)
    print("Running Verifier Test Suite...")
    print("=" * 60)
    res2 = subprocess.run(
        [sys.executable, "-m", "pytest", "verifier/tests", "-v"],
        cwd=REPO_ROOT,
    )

    if res1.returncode != 0 or res2.returncode != 0:
        print("\nOne or more test suites failed.")
        sys.exit(1)

    print("\nAll test suites passed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    run_tests()
