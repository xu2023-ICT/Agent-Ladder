"""Minimal `terminal` tool facade modeled after Hermes."""

from __future__ import annotations

from .environments import LocalEnvironment
from .environments.base import DEFAULT_TIMEOUT

NAME = "terminal"

DESCRIPTION = (
    "Execute a shell command. Filesystem, current working directory, and "
    "exported environment variables persist between calls -- if you `cd` "
    "somewhere or `export` a variable in one call, it is still in effect on "
    "the next call, so there is no need to re-`cd` or re-export on every "
    "call. Returns combined stdout+stderr, followed by the exit code. This "
    "is the only tool available -- use it for everything: listing/reading "
    "files, searching, editing with sed/heredocs, running tests, and any "
    "other terminal operation."
)

SCHEMA = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Full shell command string to run, e.g. `ls -la` or `pytest tests/ -x`.",
                },
                "timeout": {
                    "type": "number",
                    "description": f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
                },
            },
            "required": ["command"],
        },
    },
}


class TerminalTool:
    def __init__(self, environment: LocalEnvironment | None = None):
        self.environment = environment or LocalEnvironment()

    def run(self, command: str, timeout: float = DEFAULT_TIMEOUT) -> str:
        return self.environment.execute(command=command, timeout=timeout)

    def cleanup(self) -> None:
        self.environment.cleanup()
