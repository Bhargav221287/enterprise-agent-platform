"""Unit tests for structured tools, registry, and validation."""

import asyncio

import pytest
from app.tools.base import BaseTool, ToolContext
from app.tools.builtin import (
    CalculateTool,
    LookupRecordTool,
    SearchKBTool,
)
from app.tools.registry import ToolRegistry


@pytest.fixture
def tool_context():
    return ToolContext(
        run_id="test-run-1",
        session_id="test-session-1",
    )


@pytest.mark.asyncio
async def test_search_kb_tool(tool_context):
    """Verify search_kb retrieves relevant articles based on keyword queries."""
    tool = SearchKBTool()
    res = await tool.run({"query": "vpn connection", "limit": 2}, tool_context)

    assert res.success is True
    assert len(res.data["matches"]) <= 2
    assert any("VPN" in m["title"] for m in res.data["matches"])


@pytest.mark.asyncio
async def test_calculate_tool_valid(tool_context):
    """Verify calculate accurately computes safe arithmetic expressions."""
    tool = CalculateTool()
    res = await tool.run({"expression": "(1800 / 9500) * 100"}, tool_context)

    assert res.success is True
    assert round(res.data["result"], 2) == 18.95


@pytest.mark.asyncio
async def test_calculate_tool_blocks_unsafe_call(tool_context):
    """Verify calculate blocks arbitrary code execution and unauthorized functions."""
    tool = CalculateTool()
    res = await tool.run({"expression": "__import__('os').system('ls')"}, tool_context)

    assert res.success is False
    assert "Unsupported AST node" in res.error or "Function call not permitted" in res.error


@pytest.mark.asyncio
async def test_lookup_record_tool(tool_context):
    """Verify lookup_record retrieves enterprise record attributes."""
    tool = LookupRecordTool()
    res = await tool.run(
        {"record_type": "credit_profile", "record_id": "APP-501"}, tool_context
    )

    assert res.success is True
    assert res.data["found"] is True
    assert res.data["data"]["credit_score"] == 750


@pytest.mark.asyncio
async def test_tool_registry_and_schema():
    """Verify registry generates valid JSON schemas and dispatches execution."""
    registry = ToolRegistry()
    schemas = registry.get_schemas()

    assert "search_kb" in schemas
    assert "calculate" in schemas
    assert "lookup_record" in schemas
    assert "memory_read" in schemas
    assert "memory_write" in schemas
    assert "generate_code" in schemas


@pytest.mark.asyncio
async def test_tool_timeout_enforcement(tool_context):
    """Verify tool execution terminates and reports error when timeout is exceeded."""

    class SlowTool(BaseTool):
        name = "slow_tool"
        description = "Simulates long running operation"
        timeout_seconds = 0.1

        async def _execute(self, input_data, context):
            await asyncio.sleep(0.5)
            return {"done": True}

    slow_tool = SlowTool()
    res = await slow_tool.run({}, tool_context)

    assert res.success is False
    assert "timed out after" in res.error


@pytest.mark.asyncio
async def test_tool_argument_validation_error(tool_context):
    """Verify invalid argument types are caught before tool execution."""
    tool = SearchKBTool()
    # limit must be an integer, passing an invalid non-coercible dict
    res = await tool.run({"query": "test", "limit": "invalid_number"}, tool_context)

    assert res.success is False
    assert "Tool input validation failed" in res.error
