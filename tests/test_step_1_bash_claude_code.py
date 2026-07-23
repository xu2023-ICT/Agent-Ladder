from pathlib import Path

from agent_ladder.steps.step_1_bash.claude_code import tool as claude_tool


def test_claude_code_tracks_cwd_between_fresh_subprocesses(tmp_path: Path):
    state = claude_tool.BashState(cwd=".")
    output = claude_tool.run(f"cd {tmp_path}", state)
    assert "exit code: 0" in output
    assert state.cwd == str(tmp_path)

    output = claude_tool.run("pwd", state)
    assert str(tmp_path) in output
    assert state.cwd == str(tmp_path)
