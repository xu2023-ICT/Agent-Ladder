from agent_ladder.steps.step_1_bash.pi_mono import tool as pi_mono_tool


def test_pi_mono_folds_failures_into_tool_result_text():
    output = pi_mono_tool.execute_for_loop({"command": "exit 4"})
    assert "Command exited with code 4" in output
