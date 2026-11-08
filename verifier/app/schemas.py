"""Pydantic schemas for the automated code verification harness."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """Specification of an input-output unit test case."""

    __test__ = False

    input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments passed to the function under test",
    )
    expected_output: Any = Field(..., description="Expected return value")
    function_name: Optional[str] = Field(
        default=None, description="Optional target function name"
    )


class VerificationRequest(BaseModel):
    """Request payload to verify AI-generated Python code."""

    code: str = Field(..., description="Raw Python source code to verify")
    test_cases: List[TestCase] = Field(
        default_factory=list, description="List of test cases to execute"
    )
    timeout_seconds: float = Field(
        default=3.0, ge=0.5, le=10.0, description="Max execution timeout in seconds"
    )


class CheckResult(BaseModel):
    """Result of an individual verification gate check."""

    check_name: str
    passed: bool
    execution_time_ms: float
    violations: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class TestCaseResult(BaseModel):
    """Result of an individual test case execution."""

    test_index: int
    passed: bool
    input_data: Any
    expected_output: Any
    actual_output: Any = None
    error: Optional[str] = None


class VerificationReport(BaseModel):
    """Comprehensive structured report produced by the verification harness."""

    passed: bool
    checks: List[CheckResult] = Field(default_factory=list)
    test_results: List[TestCaseResult] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    total_execution_time_ms: float = 0.0
