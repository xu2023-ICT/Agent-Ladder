from pathlib import Path

from agent_ladder.steps.step_1_bash.hermes_agent.tool import TerminalTool


def test_hermes_terminal_session_persists_cwd_and_exported_env(tmp_path: Path):
    terminal = TerminalTool()
    try:
        output = terminal.run(f"cd {tmp_path}; export AGENT_LADDER_TEST_VALUE=ok")
        assert "Exit code: 0" in output

        output = terminal.run("pwd; printf $AGENT_LADDER_TEST_VALUE")
        assert str(tmp_path) in output
        assert "ok" in output
    finally:
        terminal.cleanup()
