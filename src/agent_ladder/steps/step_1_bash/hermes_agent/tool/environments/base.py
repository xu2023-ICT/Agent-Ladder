"""Minimal Hermes-style execution environment.

Hermes keeps the terminal API in `tools/terminal_tool.py`, while real command
execution is delegated to `tools/environments/*`. The important Step 1 idea is
the base environment's spawn-per-call wrapper: source a snapshot, run command,
write a new snapshot, and emit a cwd marker.
"""

from __future__ import annotations

import os
import re
import tempfile
from abc import ABC, abstractmethod

DEFAULT_TIMEOUT = 180.0
MAX_OUTPUT_CHARS = 20_000

_CWD_MARKER = "__AGENT_LADDER_TERMINAL_CWD__"
_CWD_RE = re.compile(re.escape(_CWD_MARKER) + r"(.*?)" + re.escape(_CWD_MARKER), re.DOTALL)


class BaseEnvironment(ABC):
    def __init__(self, cwd: str | None = None):
        self.cwd = cwd or os.getcwd()
        fd, self._snapshot_path = tempfile.mkstemp(prefix="agent-ladder-terminal-", suffix=".env")
        os.close(fd)

    @abstractmethod
    def _run_bash(self, script: str, timeout: float) -> tuple[str, int | None, bool]:
        """Run a prepared bash script and return output, exit code, timed-out flag."""

    def execute(self, command: str, timeout: float = DEFAULT_TIMEOUT) -> str:
        wrapped = self._wrap_command(command)
        output, exit_code, timed_out = self._run_bash(wrapped, timeout=timeout)

        output, new_cwd = self._extract_cwd(output)
        if new_cwd and os.path.isdir(new_cwd):
            self.cwd = new_cwd

        output = self._truncate((output or "").strip() or "(no output)")
        if timed_out:
            return f"{output}\n\nCommand timed out after {timeout}s."
        return f"{output}\n\nExit code: {exit_code}"

    def _wrap_command(self, command: str) -> str:
        return (
            f"source {self._snapshot_path} 2>/dev/null\n"
            f"{command}\n"
            "__agent_ladder_exit=$?\n"
            f"export -p > {self._snapshot_path} 2>/dev/null\n"
            f"printf '\\n{_CWD_MARKER}%s{_CWD_MARKER}\\n' \"$(pwd)\"\n"
            "exit $__agent_ladder_exit\n"
        )

    @staticmethod
    def _extract_cwd(output: str) -> tuple[str, str | None]:
        match = _CWD_RE.search(output or "")
        if not match:
            return output, None
        return output[: match.start()] + output[match.end() :], match.group(1).strip()

    @staticmethod
    def _truncate(text: str) -> str:
        if len(text) <= MAX_OUTPUT_CHARS:
            return text
        hidden = len(text) - MAX_OUTPUT_CHARS
        return f"{text[:MAX_OUTPUT_CHARS]}\n...[truncated, {hidden} more chars]"

    def cleanup(self) -> None:
        try:
            os.unlink(self._snapshot_path)
        except OSError:
            pass
