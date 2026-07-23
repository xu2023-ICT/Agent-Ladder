"""Local Hermes-style terminal environment."""

from __future__ import annotations

import subprocess

from .base import BaseEnvironment


class LocalEnvironment(BaseEnvironment):
    """Spawn a fresh bash process for every command, preserving cwd/export state."""

    def _run_bash(self, script: str, timeout: float) -> tuple[str, int | None, bool]:
        try:
            completed = subprocess.run(
                ["bash", "-c", script],
                cwd=self.cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                text=True,
            )
            return completed.stdout, completed.returncode, False
        except subprocess.TimeoutExpired as exc:
            output = exc.output or ""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            return output, None, True
