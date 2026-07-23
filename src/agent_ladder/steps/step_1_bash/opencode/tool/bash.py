"""The bash tool: run.py's only way to observe or change anything outside chat.

No dedicated ls/cat/grep/sed/edit/test-runner tools -- one shell command
string, run to completion, stdout+stderr merged into one string. Splitting
that into dedicated read/edit/search tools is later chapters' job.

Parameter shape and execution model both come straight from opencode's real
`bash`/`shell` tool (`reference-agents/opencode/packages/opencode/src/tool/
shell.ts` and its V2 rewrite `packages/core/src/tool/bash.ts`, see
`../README.md`): a `command`
(required) + `timeout` (optional, defaulted) pair, no shell-type selection,
no env injection. opencode also exposes an optional `workdir` so the model
doesn't have to `cd && command`; left out here to keep the surface to the
two fields that both opencode and kimi-cli agree are load-bearing (see
`../../kimi/README.md`) -- the model just
`cd`s inside the command string like kimi-cli's variant does.
"""

from agent_ladder.steps.step_1_bash.opencode.tool.executor import execute
from agent_ladder.steps.step_1_bash.opencode.tool.schema import DEFAULT_TIMEOUT, NAME, SCHEMA


def run(command: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Execute `command` in a fresh shell, returning merged stdout+stderr plus exit status.

    Mirrors the reference agents' execution model: a brand new subprocess
    per call (no persistent shell to leak cwd/env between calls), stdin
    closed so an interactive prompt (e.g. git asking for a password) can't
    hang the call forever, and a hard timeout that kills the process rather
    than trusting it to finish on its own.
    """
    return execute(command=command, timeout=timeout)
