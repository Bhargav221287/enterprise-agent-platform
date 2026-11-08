"""Tool Registry for registering, retrieving, and invoking structured tools."""

import logging
from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool, ToolContext, ToolResult
from app.tools.builtin import (
    CalculateTool,
    GenerateCodeTool,
    LookupRecordTool,
    MemoryReadTool,
    MemoryWriteTool,
    SearchKBTool,
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry maintaining available structured tools with validation and dispatch."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the platform's standard built-in tools."""
        self.register(SearchKBTool())
        self.register(CalculateTool())
        self.register(LookupRecordTool())
        self.register(MemoryReadTool())
        self.register(MemoryWriteTool())
        self.register(GenerateCodeTool())

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return sorted(list(self._tools.keys()))

    def get_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Return JSON schema definitions for all registered tools."""
        schemas = {}
        for name, tool in self._tools.items():
            schemas[name] = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema.model_json_schema(),
                "output_schema": tool.output_schema.model_json_schema(),
            }
        return schemas

    async def invoke(
        self, tool_name: str, arguments: Dict[str, Any], context: ToolContext
    ) -> ToolResult:
        """Invoke a tool with validation, error handling, and telemetry."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' is not registered. Available tools: {self.list_tools()}",
            )
        return await tool.run(arguments, context)
