from pathlib import Path

from agent_ladder.steps.step_1_bash.qwen_code import tool as qwen_tool


def test_qwen_code_fresh_subprocess_does_not_persist_cwd(tmp_path: Path):
    assert "[exit code: 0]" in qwen_tool.run(f"cd {tmp_path}")
    assert str(tmp_path) not in qwen_tool.run("pwd")
