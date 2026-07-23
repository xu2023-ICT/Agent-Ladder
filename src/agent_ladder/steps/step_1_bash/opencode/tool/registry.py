"""Minimal opencode ToolRegistry analogue."""

from agent_ladder.steps.step_1_bash.opencode.tool.schema import NAME, SCHEMA
from agent_ladder.steps.step_1_bash.opencode.tool.bash import run


def ids() -> list[str]:
    return [NAME]


def tools() -> list[dict]:
    return [SCHEMA]


def execute(name: str, **params) -> str:
    if name != NAME:
        raise KeyError(name)
    return run(**params)
