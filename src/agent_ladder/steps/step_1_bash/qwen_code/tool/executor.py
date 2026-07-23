"""qwen-code style invocation/executor layer for the shell tool."""

import subprocess

from agent_ladder.steps.step_1_bash.qwen_code.tool.truncation import truncate_tool_output


class ShellToolInvocation:
    def __init__(self, params: dict):
        self.params = params

    def execute(self) -> str:
        command = self.params["command"]
        timeout = self.params.get("timeout")
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
            output = truncate_tool_output(exc.output or "")
            return f"{output}\n[command timed out after {timeout}s and was killed]"

        return f"{truncate_tool_output(completed.stdout or '')}\n[exit code: {completed.returncode}]"
