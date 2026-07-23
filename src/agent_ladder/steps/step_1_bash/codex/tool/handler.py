"""Codex-style shell_command handler."""

import subprocess
import time

from agent_ladder.steps.step_1_bash.codex.tool.schema import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_OUTPUT_CHARS,
)
from agent_ladder.steps.step_1_bash.codex.tool.shell import run_command


def run(command: str, workdir: str | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Execute `command` and format the result for the model."""
    start = time.monotonic()
    try:
        completed = run_command(command, workdir, timeout)
        output, exit_code, timed_out = completed.stdout, completed.returncode, False
    except subprocess.TimeoutExpired as exc:
        raw_output = exc.output or b""
        output = raw_output.decode(errors="replace") if isinstance(raw_output, bytes) else raw_output
        exit_code, timed_out = None, True
    except OSError as exc:
        duration = time.monotonic() - start
        return _format(str(exc), 1, duration, False)
    duration = time.monotonic() - start

    return _format(output, exit_code, duration, timed_out)


def _format(output: str, exit_code: int | None, duration: float, timed_out: bool) -> str:
    lines = []
    if timed_out:
        lines.append(f"command timed out after {duration * 1000:.0f} milliseconds")
    else:
        lines.append(f"Exit code: {exit_code}")
    lines.append(f"Wall time: {duration:.1f} seconds")

    total_lines = output.count("\n") + 1 if output else 0
    truncated = _truncate_middle(output, MAX_OUTPUT_CHARS)
    if truncated != output:
        lines.append(f"Total output lines: {total_lines}")
    lines.append("Output:")
    lines.append(truncated if truncated else "(no output)")
    return "\n".join(lines)


def _truncate_middle(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    keep = max_chars // 2
    omitted = len(text) - 2 * keep
    return f"{text[:keep]}\n... [{omitted} chars omitted] ...\n{text[-keep:]}"
