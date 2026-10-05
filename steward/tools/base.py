"""
BaseTool interface and execution result specification.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool = True
    output: str = ""
    diff: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "diff": self.diff,
            "error": self.error,
            "data": self.data,
        }


class BaseTool(ABC):
    """Abstract base class for all agent execution tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool signature to OpenAI/NIM compatible JSON function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Asynchronously execute the tool with given arguments."""
        pass
