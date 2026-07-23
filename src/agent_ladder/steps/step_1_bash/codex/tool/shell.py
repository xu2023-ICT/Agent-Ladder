"""Minimal shell adapter for the Codex-style shell_command tool."""

import subprocess


def derive_exec_args(command: str, login: bool = True) -> list[str]:
    arg = "-lc" if login else "-c"
    return ["bash", arg, command]


def run_command(command: str, workdir: str | None, timeout: float):
    return subprocess.run(
        derive_exec_args(command),
        cwd=workdir,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
