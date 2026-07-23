"""The bash tool, grounded in kimi-cli's real `Shell` tool.

Investigated `reference-agents/kimi-cli` (Python; `src/kimi_cli/tools/shell/
__init__.py` + its prompt template `bash.md`, see
`../README.md` for the full writeup) rather
than guessed:

- Params are exactly `command` (required) + `timeout` (default 60s). The
  real tool also has `run_in_background` + `description` for spawning a
  background task, gated behind a whole separate notification/`TaskOutput`/
  `TaskStop` mechanism (`kimi_cli.background`) -- that's a distinct feature
  from "one universal shell tool" and is left out here on purpose.
- No `cwd`/`workdir` parameter: the model `cd`s inside `command` itself.
- Execution model (`shell/__init__.py:221-264`, `_run_shell_command`): every
  call is a brand-new `bash -c command` subprocess, nothing persisted from
  the previous call (no cwd, no env, no history) -- kimi-cli's own tool
  description says this outright. stdin is closed immediately so an
  interactive prompt (e.g. git asking for a password) hits EOF instead of
  hanging until the timeout kills it. stdout and stderr are written into the
  *same* buffer as they arrive, not kept as two separate strings.
- Foreground commands are capped at `MAX_FOREGROUND_TIMEOUT = 5 * 60`
  seconds; the real tool raises a validation error above that and tells the
  model to use `run_in_background=true` instead. Since background execution
  isn't implemented here, `run()` just clamps to that same 300s ceiling.
- Success and failure are reported asymmetrically, straight out of
  `ToolResultBuilder.ok()`/`.error()` (`tools/utils.py`): a clean exit just
  returns the raw merged output, no exit-code noise; a non-zero exit
  appends the exit code plus a short tail of the last non-empty output
  lines, so the model doesn't have to scroll a long build log to find the
  actual error -- kimi-cli's `tail()` helper does this for real; this
  reimplements the same idea (last few non-empty lines) without the rest of
  `ToolResultBuilder`'s char/line-budget bookkeeping.

Left out on purpose (production concerns from kimi-cli, not this step's
teaching goal): approval/confirmation before running a command
(`self._approval.request(...)`), background tasks, and the fine-grained
50,000-char / 2,000-char-per-line truncation budget in `ToolResultBuilder`
-- a single crude character cap stands in for it here.
"""

import subprocess

from agent_ladder.steps.step_1_bash.kimi.tool.result import ToolResultBuilder
from agent_ladder.steps.step_1_bash.kimi.tool.schema import DEFAULT_TIMEOUT, MAX_FOREGROUND_TIMEOUT, SCHEMA

def run(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run `command` in a fresh `bash -c` subprocess, kimi-cli Shell style.

    One subprocess per call (no persistent shell to leak cwd/env between
    calls), stdin closed so an interactive prompt can't hang the call
    forever, and a hard timeout that kills the process rather than trusting
    it to finish on its own. On success, returns the raw merged
    stdout+stderr; on a non-zero exit, appends the exit code and a short
    tail of the last non-empty output lines, mirroring kimi-cli's
    `ToolResultBuilder.ok()` vs `.error()` split.
    """
    timeout = min(timeout or DEFAULT_TIMEOUT, MAX_FOREGROUND_TIMEOUT)
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
        builder = ToolResultBuilder()
        builder.write(exc.output or "")
        output = builder.output()
        return f"{output}\n(command killed by timeout after {timeout}s)".strip()

    builder = ToolResultBuilder()
    builder.write(completed.stdout or "")
    output = builder.output()
    if completed.returncode == 0:
        return output or "(no output)"

    brief = _tail(output)
    result = f"{output}\n(exit code: {completed.returncode})"
    if brief:
        result += f"\n(tail: {brief})"
    return result


def _tail(output: str, max_lines: int = 5, max_line_len: int = 200) -> str:
    """Last non-empty lines of `output`, most recent last -- kimi-cli's `tail()`."""
    collected = []
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) > max_line_len:
            stripped = stripped[:max_line_len] + "..."
        collected.append(stripped)
        if len(collected) >= max_lines:
            break
    return "\n".join(reversed(collected))
