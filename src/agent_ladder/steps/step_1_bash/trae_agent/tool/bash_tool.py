"""Minimal Trae-agent-style persistent bash tool."""

from __future__ import annotations

import os
import re
import subprocess
import threading
import uuid
from functools import cached_property

from .base import ToolCallArguments, ToolError, ToolExecResult, ToolParameter

COMMAND_TIMEOUT = 120


class _BashSession:
    def __init__(self):
        self._sentinel = f"___AGENT_LADDER_BASH_DONE_{uuid.uuid4().hex}___"
        self._trailer_re = re.compile(
            re.escape(self._sentinel.encode()) + rb"(\d+)" + re.escape(self._sentinel.encode())
        )
        self.process = subprocess.Popen(
            ["/bin/bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

    def run(self, command: str) -> ToolExecResult:
        if self.process.poll() is not None:
            return ToolExecResult(
                error=(
                    f"bash has exited with return code {self.process.returncode}; "
                    "call again with restart: true"
                ),
                error_code=-1,
            )

        assert self.process.stdin is not None
        assert self.process.stdout is not None

        trailer = f"\nprintf '\\n{self._sentinel}%s{self._sentinel}\\n' \"$?\"\n"
        self.process.stdin.write(command.encode() + trailer.encode())
        self.process.stdin.flush()

        timed_out = False

        def on_timeout():
            nonlocal timed_out
            timed_out = True
            self.process.kill()

        timer = threading.Timer(COMMAND_TIMEOUT, on_timeout)
        timer.start()
        buf = b""
        try:
            while not self._trailer_re.search(buf):
                chunk = os.read(self.process.stdout.fileno(), 4096)
                if not chunk:
                    break
                buf += chunk
        finally:
            timer.cancel()

        match = self._trailer_re.search(buf)
        if match:
            output = buf[: match.start()].decode(errors="replace")
            return ToolExecResult(output=output, error_code=int(match.group(1)))
        if timed_out:
            output = buf.decode(errors="replace")
            return ToolExecResult(
                output=output,
                error=(
                    f"timed out: bash has not returned in {COMMAND_TIMEOUT} seconds; "
                    "call again with restart: true"
                ),
                error_code=-1,
            )
        return ToolExecResult(
            output=buf.decode(errors="replace"),
            error="shell exited unexpectedly; call again with restart: true",
            error_code=-1,
        )

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.kill()


class BashTool:
    def __init__(self):
        self._session: _BashSession | None = None

    @cached_property
    def name(self) -> str:
        return "bash"

    @cached_property
    def description(self) -> str:
        return (
            "Run commands in a persistent bash shell. State is persistent "
            "across command calls and discussions with the user. Use it for "
            "listing and reading files, searching, editing with sed/heredocs, "
            "running tests, and so on. Set restart to true to recreate a "
            "timed-out or exited shell session."
        )

    @cached_property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter("command", "string", "The bash command to run.", required=True),
            ToolParameter("restart", "boolean", "Set to true to restart the bash session.", required=False),
        ]

    def json_definition(self) -> dict[str, object]:
        properties = {
            parameter.name: {"type": parameter.type, "description": parameter.description}
            for parameter in self.parameters
        }
        required = [parameter.name for parameter in self.parameters if parameter.required]
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
        if arguments.get("restart"):
            if self._session is not None:
                self._session.close()
            self._session = _BashSession()

        if self._session is None:
            self._session = _BashSession()

        command = arguments.get("command")
        if not isinstance(command, str):
            if arguments.get("restart"):
                return ToolExecResult(output="tool has been restarted.")
            raise ToolError(f"No command provided for the {self.name} tool")
        return self._session.run(command)

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None


BASH_TOOL = BashTool().json_definition()
