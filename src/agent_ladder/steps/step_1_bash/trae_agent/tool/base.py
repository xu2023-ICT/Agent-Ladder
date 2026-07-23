"""Minimal Trae-agent tool base layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Protocol

ToolCallArguments = dict[str, str | int | float | bool | dict[str, object] | list[object] | None]


class ToolError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class ToolExecResult:
    output: str | None = None
    error: str | None = None
    error_code: int = 0


@dataclass
class ToolResult:
    call_id: str
    name: str
    success: bool
    result: str | None = None
    error: str | None = None
    error_code: int = 0
    id: str | None = None


@dataclass
class ToolCall:
    name: str
    call_id: str
    arguments: ToolCallArguments = field(default_factory=dict)
    id: str | None = None


@dataclass(frozen=True)
class ToolParameter:
    name: str
    type: str | list[str]
    description: str
    required: bool = True


class Tool(Protocol):
    @cached_property
    def name(self) -> str: ...

    def json_definition(self) -> dict[str, object]: ...

    def execute(self, arguments: ToolCallArguments) -> ToolExecResult: ...

    def close(self) -> None: ...


class ToolExecutor:
    def __init__(self, tools: list[Tool]):
        self._tools = tools
        self._tool_map = {self._normalize_name(tool.name): tool for tool in tools}

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.lower().replace("_", "")

    def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        normalized_name = self._normalize_name(tool_call.name)
        tool = self._tool_map.get(normalized_name)
        if tool is None:
            return ToolResult(
                name=tool_call.name,
                success=False,
                error=f"Tool '{tool_call.name}' not found.",
                call_id=tool_call.call_id,
                id=tool_call.id,
            )

        try:
            tool_exec_result = tool.execute(tool_call.arguments)
            return ToolResult(
                name=tool_call.name,
                success=tool_exec_result.error_code == 0,
                result=tool_exec_result.output,
                error=tool_exec_result.error,
                error_code=tool_exec_result.error_code,
                call_id=tool_call.call_id,
                id=tool_call.id,
            )
        except Exception as exc:
            return ToolResult(
                name=tool_call.name,
                success=False,
                error=f"Error executing tool '{tool_call.name}': {exc}",
                call_id=tool_call.call_id,
                id=tool_call.id,
            )

    def sequential_tool_call(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        return [self.execute_tool_call(tool_call) for tool_call in tool_calls]

    def close_tools(self) -> None:
        for tool in self._tools:
            tool.close()
