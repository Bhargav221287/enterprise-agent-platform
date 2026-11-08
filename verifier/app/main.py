"""Enterprise Agent Platform Verifier Service FastAPI Application."""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from app.checks import check_syntax, scan_safety_ast
from app.sandbox import execute_sandboxed_tests
from app.schemas import CheckResult, TestCaseResult, VerificationReport, VerificationRequest
from app.telemetry import setup_telemetry
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

tracer: Optional[trace.Tracer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing telemetry and sandbox environment."""
    global tracer
    service_name = os.getenv("OTEL_SERVICE_NAME", "verifier-service")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    tracer = setup_telemetry(service_name=service_name, otlp_endpoint=otlp_endpoint)
    logger.info("Verifier Service started successfully on port 8001")
    yield
    logger.info("Verifier Service shut down cleanly.")


app = FastAPI(
    title="Enterprise Agent Platform - Verifier Service",
    description="Automated multi-stage AST safety scanner and sandboxed code verification harness.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)


@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint for verifier microservice."""
    return {"status": "ok", "service": "verifier-service"}


@app.post("/verify", response_model=VerificationReport, tags=["Verification"])
async def verify_code(req: VerificationRequest, request: Request):
    """Verify AI-generated Python code through syntax, AST safety, and sandboxed execution."""
    total_start = time.perf_counter()

    # Extract propagated OpenTelemetry distributed trace context from orchestrator
    propagator = TraceContextTextMapPropagator()
    parent_ctx = propagator.extract(carrier=dict(request.headers))

    with tracer.start_as_current_span(
        "verifier.verify",
        context=parent_ctx,
        attributes={
            "verifier.test_cases_count": len(req.test_cases),
            "verifier.timeout_seconds": req.timeout_seconds,
        },
    ) as span:
        checks_list: List[CheckResult] = []
        test_results: List[TestCaseResult] = []

        # Stage 1: Syntax Analysis
        syntax_res = check_syntax(req.code)
        checks_list.append(syntax_res)
        if not syntax_res.passed:
            total_duration = (time.perf_counter() - total_start) * 1000
            span.set_attribute("verifier.passed", False)
            span.set_attribute("verifier.failed_stage", "syntax_check")
            return VerificationReport(
                passed=False,
                checks=checks_list,
                test_results=[],
                summary={
                    "stage_failed": "syntax_check",
                    "checks_passed": 0,
                    "checks_total": 3,
                    "tests_passed": 0,
                    "tests_total": len(req.test_cases),
                },
                total_execution_time_ms=round(total_duration, 2),
            )

        # Stage 2: AST Static Safety Scan
        safety_res = scan_safety_ast(req.code)
        checks_list.append(safety_res)
        if not safety_res.passed:
            total_duration = (time.perf_counter() - total_start) * 1000
            span.set_attribute("verifier.passed", False)
            span.set_attribute("verifier.failed_stage", "ast_safety_scan")
            span.set_attribute("verifier.violations", safety_res.violations)
            return VerificationReport(
                passed=False,
                checks=checks_list,
                test_results=[],
                summary={
                    "stage_failed": "ast_safety_scan",
                    "violations": safety_res.violations,
                    "checks_passed": 1,
                    "checks_total": 3,
                    "tests_passed": 0,
                    "tests_total": len(req.test_cases),
                },
                total_execution_time_ms=round(total_duration, 2),
            )

        # Stage 3 & 4: Sandboxed Subprocess Execution and Test Assertions
        sandbox_res, test_results = execute_sandboxed_tests(
            code=req.code,
            test_cases=req.test_cases,
            timeout_seconds=req.timeout_seconds,
        )
        checks_list.append(sandbox_res)

        tests_passed_count = sum(1 for t in test_results if t.passed)
        overall_passed = sandbox_res.passed and (
            tests_passed_count == len(test_results) or len(test_results) == 0
        )

        total_duration = (time.perf_counter() - total_start) * 1000
        span.set_attribute("verifier.passed", overall_passed)

        checks_passed_count = sum(1 for c in checks_list if c.passed)
        summary_payload: Dict[str, Any] = {
            "checks_passed": checks_passed_count,
            "checks_total": len(checks_list),
            "tests_passed": tests_passed_count,
            "tests_total": len(test_results),
            "all_tests_passed": tests_passed_count == len(test_results),
        }
        if not overall_passed:
            summary_payload["error"] = sandbox_res.error

        return VerificationReport(
            passed=overall_passed,
            checks=checks_list,
            test_results=test_results,
            summary=summary_payload,
            total_execution_time_ms=round(total_duration, 2),
        )
