"""Claude Code style Bash tool handler.

Mirrors the reference BashTool split at a small scale: schema lives in
`schema.py`, cwd lives in `state.py`, and this file owns command execution plus
model-facing output formatting.
"""

import re
import subprocess
import uuid

from agent_ladder.steps.step_1_bash.claude_code.tool.schema import (
    DEFAULT_TIMEOUT,
    MAX_OUTPUT_CHARS,
)
from agent_ladder.steps.step_1_bash.claude_code.tool.state import BashState

_TOKEN = uuid.uuid4().hex
_EXIT_MARKER = f"@AL_EXIT_{_TOKEN}@"
_CWD_MARKER = f"@AL_CWD_{_TOKEN}@"
_TRAILER_RE = re.compile(
    re.escape(_EXIT_MARKER)
    + r"(.*?)"
    + re.escape(_EXIT_MARKER)
    + re.escape(_CWD_MARKER)
    + r"(.*?)"
    + re.escape(_CWD_MARKER),
    re.DOTALL,
)


def run(command: str, state: BashState, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Run `command` in a fresh subprocess and update persistent cwd state."""
    output, next_cwd = _run_bash(command, state.cwd, timeout)
    state.cwd = next_cwd
    return output


def _run_bash(command: str, cwd: str, timeout: float) -> tuple[str, str]:
    wrapped = (
        f"{command}\n"
        f"__al_exit=$?\n"
        f'printf "{_EXIT_MARKER}%s{_EXIT_MARKER}{_CWD_MARKER}%s{_CWD_MARKER}" "$__al_exit" "$PWD"\n'
    )
    try:
        result = subprocess.run(
            ["bash", "-c", wrapped],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s.", cwd

    stdout = result.stdout
    match = _TRAILER_RE.search(stdout)
    if match:
        exit_code, next_cwd = match.group(1), match.group(2)
        stdout = stdout[: match.start()]
    else:
        exit_code, next_cwd = str(result.returncode), cwd

    parts = []
    if stdout.strip():
        parts.append(_truncate(stdout.rstrip("\n")))
    if result.stderr.strip():
        parts.append("stderr:\n" + _truncate(result.stderr.rstrip("\n")))
    parts.append(f"exit code: {exit_code}")
    return "\n".join(parts), (next_cwd or cwd)


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    omitted = len(text) - MAX_OUTPUT_CHARS
    return text[:MAX_OUTPUT_CHARS] + f"\n... [{omitted} more characters truncated] ..."
