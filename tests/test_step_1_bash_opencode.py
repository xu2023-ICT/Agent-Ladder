from pathlib import Path

from agent_ladder.steps.step_1_bash.opencode import tool as opencode_tool


def test_opencode_fresh_subprocess_does_not_persist_cwd(tmp_path: Path):
    assert "Exit code: 0" in opencode_tool.run(f"cd {tmp_path}")
    assert str(tmp_path) not in opencode_tool.run("pwd")
