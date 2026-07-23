"""Minimal qwen-code ToolRegistry analogue."""

from agent_ladder.steps.step_1_bash.qwen_code.tool.schema import NAME, SCHEMA
from agent_ladder.steps.step_1_bash.qwen_code.tool.shell import run


class ToolRegistry:
    def __init__(self):
        self._tools = {NAME: (SCHEMA, run)}

    def schema(self, name: str = NAME) -> dict:
        return self._tools[name][0]

    def execute(self, name: str, **params) -> str:
        return self._tools[name][1](**params)
