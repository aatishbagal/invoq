from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from invoq.mcp.capabilities import ToolCapabilities


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    capabilities: ToolCapabilities
    input_schema: type[BaseModel]
    parameters: List[ToolParameter] = field(default_factory=list)

    def to_ollama_format(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema.model_json_schema(),
            },
        }


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class ToolResult:
    call_id: Optional[str]
    success: bool
    output: str
    error: Optional[str] = None


__all__ = [
    "ToolParameter",
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
]
