"""Executes the `bash` tool: a fresh, non-interactive subprocess per call."""

import subprocess

from agent_ladder.steps.step_1_bash.minicode.tool.schema import DEFAULT_TIMEOUT

MAX_OUTPUT_CHARS = 20_000


def run_bash(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run `command` in a fresh, non-interactive bash subprocess.

    This is where the model's tool call actually turns into a real, running
    process. The model only ever produced a JSON string like
    `{"command": "ls -la"}`; whoever calls this function has already parsed
    that JSON, so by the time we get here `command` is just a plain string.
    """
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            stdin=subprocess.DEVNULL,  # no stdin -- a command that tries to read from it hits EOF instead of hanging
            capture_output=True,  # capture stdout/stderr instead of printing straight to the terminal
            text=True,  # decode stdout/stderr as str, not raw bytes
            timeout=timeout,  # kill the subprocess if it runs longer than this many seconds
        )
    except subprocess.TimeoutExpired:
        return f"(command timed out after {timeout}s)"

    # The model only sees this merged string, not separate stdout/stderr streams.
    output = result.stdout + result.stderr
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n[...truncated]"
    if result.returncode != 0:
        # A non-zero exit code doesn't raise in Python -- we have to check it
        # ourselves and fold it into the text, since this string is all the
        # model will ever see of what happened.
        output += f"\n(exit code: {result.returncode})"
    return output or "(no output)"
