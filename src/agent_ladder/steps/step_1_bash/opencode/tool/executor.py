"""Execution half of the opencode-style bash tool."""

import subprocess

from agent_ladder.steps.step_1_bash.opencode.tool.truncate import output as truncate_output


def execute(command: str, timeout: float) -> str:
    try:
        completed = subprocess.run(
            ["bash", "-c", command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.output or ""
        return f"{truncate_output(output)}\n\nCommand timed out after {timeout}s."

    output = completed.stdout or "(no output)"
    return f"{truncate_output(output)}\n\nExit code: {completed.returncode}"
