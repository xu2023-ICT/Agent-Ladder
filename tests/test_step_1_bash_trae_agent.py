from pathlib import Path

from agent_ladder.steps.step_1_bash.trae_agent.tool import BashTool, ToolCall, ToolExecutor


def run_trae_bash(executor: ToolExecutor, command: str, restart: bool = False) -> str:
    result = executor.execute_tool_call(
        ToolCall(name="bash", call_id="manual", arguments={"command": command, "restart": restart})
    )
    output = result.result or ""
    if result.error:
        output = f"{output}\n{result.error}".strip()
    return f"{output}\nExit code: {result.error_code}"


def test_trae_agent_persistent_shell_persists_cwd_and_can_restart(tmp_path: Path):
    executor = ToolExecutor([BashTool()])
    try:
        output = run_trae_bash(executor, f"cd {tmp_path}", restart=True)
        assert "Exit code: 0" in output

        output = run_trae_bash(executor, "pwd")
        assert str(tmp_path) in output

        output = run_trae_bash(executor, "false")
        assert "Exit code: 1" in output

        output = run_trae_bash(executor, "exit 7")
        assert "restart: true" in output

        output = run_trae_bash(executor, "echo after-dead-shell")
        assert "restart: true" in output

        output = run_trae_bash(executor, "echo restarted", restart=True)
        assert "restarted" in output
    finally:
        executor.close_tools()


def test_trae_agent_command_output_can_contain_old_fixed_sentinel():
    executor = ToolExecutor([BashTool()])
    try:
        output = run_trae_bash(executor, "printf ___AGENT_LADDER_BASH_DONE___", restart=True)
        assert "___AGENT_LADDER_BASH_DONE___" in output
        assert "Exit code: 0" in output
    finally:
        executor.close_tools()
