"""Sandboxed subprocess execution harness for running AI-generated code and test cases."""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

from app.schemas import CheckResult, TestCase, TestCaseResult

logger = logging.getLogger(__name__)


RUNNER_SCRIPT_TEMPLATE = '''
import json
import sys
import candidate_code

def run_tests():
    with open("test_spec.json", "r", encoding="utf-8") as f:
        specs = json.load(f)

    test_cases = specs.get("test_cases", [])
    results = []

    # Locate candidate function
    target_func = None
    for name in dir(candidate_code):
        attr = getattr(candidate_code, name)
        if callable(attr) and not name.startswith("_"):
            target_func = attr
            break

    if not target_func:
        with open("results.json", "w", encoding="utf-8") as f:
            json.dump({
                "status": "error",
                "error": "No callable function found in candidate code",
                "test_results": []
            }, f)
        sys.exit(0)

    all_passed = True
    for idx, tc in enumerate(test_cases):
        func_name = tc.get("function_name")
        func = getattr(candidate_code, func_name) if func_name and hasattr(candidate_code, func_name) else target_func

        inp = tc.get("input", {})
        expected = tc.get("expected_output")

        try:
            if isinstance(inp, dict):
                actual = func(**inp)
            elif isinstance(inp, list):
                actual = func(*inp)
            elif inp is not None:
                actual = func(inp)
            else:
                actual = func()

            passed = (actual == expected)
            if not passed:
                all_passed = False

            results.append({
                "test_index": idx + 1,
                "passed": passed,
                "input_data": inp,
                "expected_output": expected,
                "actual_output": actual,
                "error": None
            })
        except Exception as exc:
            all_passed = False
            results.append({
                "test_index": idx + 1,
                "passed": False,
                "input_data": inp,
                "expected_output": expected,
                "actual_output": None,
                "error": f"{type(exc).__name__}: {str(exc)}"
            })

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump({
            "status": "success",
            "all_passed": all_passed,
            "test_results": results
        }, f)

if __name__ == "__main__":
    run_tests()
'''


def _get_preexec_fn():
    """Configure resource limits on POSIX platforms using the resource module."""
    if sys.platform != "win32":
        try:
            import resource

            def set_limits():
                # Limit CPU time to 2 seconds
                resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
                # Limit address space / memory to 256MB
                resource.setrlimit(
                    resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024)
                )
                # Limit file descriptors to 32
                resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

            return set_limits
        except ImportError:
            pass
    return None


def execute_sandboxed_tests(
    code: str,
    test_cases: List[TestCase],
    timeout_seconds: float = 3.0,
) -> Tuple[CheckResult, List[TestCaseResult]]:
    """Execute candidate Python code inside an isolated subprocess with limits and run test cases."""
    start_time = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="verifier_sandbox_") as temp_dir:
        temp_path = Path(temp_dir)

        # 1. Write candidate code
        candidate_file = temp_path / "candidate_code.py"
        candidate_file.write_text(code, encoding="utf-8")

        # 2. Write test specifications
        spec_file = temp_path / "test_spec.json"
        spec_data = {
            "test_cases": [tc.model_dump() for tc in test_cases],
        }
        spec_file.write_text(json.dumps(spec_data), encoding="utf-8")

        # 3. Write runner harness
        runner_file = temp_path / "runner.py"
        runner_file.write_text(RUNNER_SCRIPT_TEMPLATE, encoding="utf-8")

        # Minimal sanitized environment
        clean_env = {
            "PYTHONPATH": temp_dir,
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
        }

        # 4. Spawn subprocess with isolation
        try:
            process = subprocess.run(
                [sys.executable, str(runner_file)],
                cwd=temp_dir,
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                preexec_fn=_get_preexec_fn(),
            )
            duration_ms = (time.perf_counter() - start_time) * 1000

            results_file = temp_path / "results.json"
            if not results_file.exists():
                err_msg = process.stderr.strip() or process.stdout.strip() or "Harness execution failed"
                return (
                    CheckResult(
                        check_name="sandboxed_execution",
                        passed=False,
                        execution_time_ms=round(duration_ms, 2),
                        error=f"Subprocess terminated with code {process.returncode}: {err_msg}",
                    ),
                    [],
                )

            with open(results_file, "r", encoding="utf-8") as f:
                output_payload = json.load(f)

            if output_payload.get("status") == "error":
                return (
                    CheckResult(
                        check_name="sandboxed_execution",
                        passed=False,
                        execution_time_ms=round(duration_ms, 2),
                        error=output_payload.get("error"),
                    ),
                    [],
                )

            test_case_results = [
                TestCaseResult(**r) for r in output_payload.get("test_results", [])
            ]
            all_passed = output_payload.get("all_passed", False) and process.returncode == 0

            return (
                CheckResult(
                    check_name="sandboxed_execution",
                    passed=all_passed,
                    execution_time_ms=round(duration_ms, 2),
                    error=None if all_passed else "One or more test assertions failed",
                ),
                test_case_results,
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return (
                CheckResult(
                    check_name="sandboxed_execution",
                    passed=False,
                    execution_time_ms=round(duration_ms, 2),
                    error=f"Sandboxed execution exceeded timeout of {timeout_seconds}s (infinite loop or hang)",
                ),
                [],
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return (
                CheckResult(
                    check_name="sandboxed_execution",
                    passed=False,
                    execution_time_ms=round(duration_ms, 2),
                    error=f"Execution error: {str(exc)}",
                ),
                [],
            )
