"""`run_shell_command`: the model's only way to observe or change anything
outside this conversation.

Named and shaped after qwen-code's own shell tool (see `../README.md`)
rather than generically calling it "bash": `command` is the only thing sent
that changes what happens;
`timeout` just bounds how long we wait (default/cap taken directly from
qwen-code's `DEFAULT_FOREGROUND_TIMEOUT_MS` / hard cap). qwen-code's real
tool also exposes `is_background` and `directory`, but step 1 drops both on
purpose (research doc section 7) -- background execution needs a whole
separate task registry/notification mechanism, and `directory` is a
convenience the model can already get by putting `cd` in `command`.

One more deliberate divergence from qwen-code's *current* prompt: its tool
description tells the model NOT to use this for cat/grep/find/sed and to
use dedicated read/grep/glob/edit tools instead. Step 1 has none of those
yet, so the description below teaches the opposite -- treat this as a
Swiss-army knife. qwen-code only earned the right to say "don't use bash
for that" after it built the specialized tools; before that point (where
this step lives), bash has to do everything.
"""

from agent_ladder.steps.step_1_bash.qwen_code.tool.executor import ShellToolInvocation
from agent_ladder.steps.step_1_bash.qwen_code.tool.schema import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    NAME,
    SCHEMA,
)


def run(command: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Run `command` in a fresh `bash -c` subprocess.

    Mirrors qwen-code's execution model: one subprocess per call (no
    persistent shell to leak cwd/env between calls), stdin closed so an
    interactive prompt (git asking for a password, a bare `python` REPL)
    can't hang the call forever, and a hard timeout that kills the process
    rather than trusting it to finish on its own. stdout and stderr are
    captured on the same stream so the model sees them interleaved the way
    a terminal would show them, not as two separate blocks.
    """
    timeout = min(timeout or DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS)
    return ShellToolInvocation({"command": command, "timeout": timeout}).execute()
