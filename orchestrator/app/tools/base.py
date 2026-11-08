"""Base interfaces and context for structured tools in the platform."""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Type

from opentelemetry import trace
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("orchestrator-tools")


class ToolContext(BaseModel):
    """Runtime context provided to tools during execution."""

    run_id: str
    session_id: str
    memory_store: Any = None
    llm_provider: Any = None
    verifier_url: str = "http://localhost:8001"

    model_config = {"arbitrary_types_allowed": True}


class ToolResult(BaseModel):
    """Result envelope of a structured tool invocation."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class EmptyToolInput(BaseModel):
    """Default empty input schema for tools without parameters."""

    model_config = {"extra": "allow"}


class EmptyToolOutput(BaseModel):
    """Default empty output schema for tools."""

    model_config = {"extra": "allow"}


class BaseTool:
    """Abstract base class for structured platform tools."""

    name: str = ""
    description: str = ""
    input_schema: Type[BaseModel] = EmptyToolInput
    output_schema: Type[BaseModel] = EmptyToolOutput
    timeout_seconds: float = 5.0

    async def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Execute the tool with input validation, timeout protection, and telemetry."""
        start_time = time.perf_counter()

        with tracer.start_as_current_span(
            f"tool.{self.name}",
            attributes={
                "tool_name": self.name,
                "run_id": context.run_id,
                "session_id": context.session_id,
            },
        ) as span:
            # 1. Input Validation
            try:
                validated_input = self.input_schema(**arguments)
            except ValidationError as val_err:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Tool input validation failed: {val_err}"
                logger.warning("[%s] %s", self.name, error_msg)
                span.set_attribute("tool.error", error_msg)
                span.set_attribute("tool.success", False)
                return ToolResult(
                    success=False,
                    error=error_msg,
                    execution_time_ms=round(duration_ms, 2),
                )

            # 2. Execution with Timeout
            try:
                raw_output = await asyncio.wait_for(
                    self._execute(validated_input, context),
                    timeout=self.timeout_seconds,
                )
                duration_ms = (time.perf_counter() - start_time) * 1000
                span.set_attribute("tool.success", True)
                span.set_attribute("tool.execution_time_ms", duration_ms)
                return ToolResult(
                    success=True,
                    data=raw_output,
                    execution_time_ms=round(duration_ms, 2),
                )
            except asyncio.TimeoutError:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Tool '{self.name}' timed out after {self.timeout_seconds}s"
                logger.error(error_msg)
                span.set_attribute("tool.error", error_msg)
                span.set_attribute("tool.success", False)
                return ToolResult(
                    success=False,
                    error=error_msg,
                    execution_time_ms=round(duration_ms, 2),
                )
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Tool '{self.name}' execution failed: {str(exc)}"
                logger.exception(error_msg)
                span.set_attribute("tool.error", error_msg)
                span.set_attribute("tool.success", False)
                return ToolResult(
                    success=False,
                    error=error_msg,
                    execution_time_ms=round(duration_ms, 2),
                )

    async def _execute(self, input_data: BaseModel, context: ToolContext) -> Any:
        """Concrete tool logic to be implemented by subclasses."""
        raise NotImplementedError
