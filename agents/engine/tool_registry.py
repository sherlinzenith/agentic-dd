from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class AgentTool:
    """
    A tool available to an AI agent.

    The LLM decides WHEN to use the tool.
    The Python function performs the actual action.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., Any]

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry containing the tools available to an agent."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        if name not in self._tools:
            raise KeyError(f"Unknown agent tool: {name}")

        return self._tools[name]

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.openai_schema() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self.get(name)
        return tool.function(**arguments)
