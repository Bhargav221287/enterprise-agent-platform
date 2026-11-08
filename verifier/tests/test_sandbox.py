"""Unit tests for subprocess sandboxed execution and test runner."""

from app.sandbox import execute_sandboxed_tests
from app.schemas import TestCase


def test_sandbox_runs_and_passes_tests():
    """Verify safe function executes in sandbox and passes test cases."""
    code = (
        "def multiply(a: int, b: int) -> int:\n"
        "    return a * b\n"
    )
    test_cases = [
        TestCase(input={"a": 3, "b": 4}, expected_output=12),
        TestCase(input={"a": -2, "b": 5}, expected_output=-10),
    ]

    check_res, test_results = execute_sandboxed_tests(code, test_cases, timeout_seconds=2.0)
    assert check_res.passed is True
    assert len(test_results) == 2
    assert all(t.passed for t in test_results)


def test_sandbox_assertion_failure():
    """Verify test failure is reported when output does not match expected."""
    code = (
        "def faulty_adder(a: int, b: int) -> int:\n"
        "    return a + b + 1\n"
    )
    test_cases = [
        TestCase(input={"a": 2, "b": 2}, expected_output=4),
    ]

    check_res, test_results = execute_sandboxed_tests(code, test_cases, timeout_seconds=2.0)
    assert check_res.passed is False
    assert len(test_results) == 1
    assert test_results[0].passed is False
    assert test_results[0].actual_output == 5


def test_sandbox_timeout_enforcement():
    """Verify infinite loop is terminated by sandbox subprocess timeout."""
    code = (
        "def infinite_loop() -> int:\n"
        "    while True:\n"
        "        pass\n"
        "    return 42\n"
    )
    test_cases = [TestCase(input={}, expected_output=42)]

    check_res, test_results = execute_sandboxed_tests(code, test_cases, timeout_seconds=1.0)
    assert check_res.passed is False
    assert "exceeded timeout" in check_res.error
