"""Compatibility shim for the split Codex shell_command tool package."""

from agent_ladder.steps.step_1_bash.codex.tool.handler import run
from agent_ladder.steps.step_1_bash.codex.tool.schema import (
    DEFAULT_TIMEOUT_SECONDS,
    DESCRIPTION,
    MAX_OUTPUT_CHARS,
    NAME,
    SCHEMA,
)

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "DESCRIPTION",
    "MAX_OUTPUT_CHARS",
    "NAME",
    "SCHEMA",
    "run",
]
