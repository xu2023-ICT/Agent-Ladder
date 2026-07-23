"""pi-mono-style bash tool surface."""

from agent_ladder.steps.step_1_bash.pi_mono.tool.errors import BashError
from agent_ladder.steps.step_1_bash.pi_mono.tool.executor import run_bash


def run(command: str, timeout: float | None = None) -> str:
    return run_bash(command, timeout=timeout)


def execute_for_loop(args: dict) -> str:
    try:
        return run(args.get("command", ""), timeout=args.get("timeout"))
    except BashError as exc:
        return f"{exc.output}\n\n{exc}" if exc.output else str(exc)
