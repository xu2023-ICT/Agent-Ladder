"""Local bash operations for the pi-mono-style tool."""

import subprocess

from agent_ladder.steps.step_1_bash.pi_mono.tool.errors import BashError
from agent_ladder.steps.step_1_bash.pi_mono.tool.output_accumulator import OutputAccumulator


def run_bash(command: str, timeout: float | None = None) -> str:
    accumulator = OutputAccumulator()
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        accumulator.append(exc.output or "")
        output = accumulator.snapshot(persist_if_truncated=True)
        raise BashError(f"Command timed out after {timeout} seconds", output) from exc

    accumulator.append(result.stdout or "")
    output = accumulator.snapshot(persist_if_truncated=True)
    if result.returncode != 0:
        raise BashError(f"Command exited with code {result.returncode}", output)
    return output
