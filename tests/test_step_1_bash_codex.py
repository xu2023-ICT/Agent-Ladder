from agent_ladder.steps.step_1_bash.codex import tool as codex_tool


def test_codex_tool_reports_invalid_workdir_as_tool_output():
    output = codex_tool.run("pwd", workdir="/definitely/not/a/real/path")
    assert "Exit code: 1" in output
    assert "No such file or directory" in output
