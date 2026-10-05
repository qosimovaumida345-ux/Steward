"""
Dynamic Tool Registry for tool discovery, validation, and execution.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry coordinating available agent tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' is not recognized in active registry.",
            )

        args = arguments or {}
        try:
            return await tool.execute(**args)
        except Exception as e:
            logger.exception("Error executing tool %s: %s", name, e)
            return ToolResult(
                success=False,
                error=f"Execution failure in tool '{name}': {str(e)}",
            )
