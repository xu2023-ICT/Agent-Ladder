from agent_ladder.steps.step_1_bash.kimi import tool
from agent_ladder.steps.step_1_bash.kimi.run import chat, step, turn


def test_run_merges_stdout_and_stderr():
    output = tool.run("echo out; echo err >&2")
    assert "out" in output
    assert "err" in output


def test_run_reports_exit_code_only_on_failure():
    ok_output = tool.run("echo fine")
    assert "exit code" not in ok_output

    failed_output = tool.run("exit 3")
    assert "exit code: 3" in failed_output


def test_run_kills_on_timeout():
    output = tool.run("sleep 5", timeout=1)
    assert "killed by timeout" in output


def test_run_does_not_hang_on_interactive_input():
    # stdin is closed, so a command reading from it hits EOF immediately
    # instead of blocking until the timeout.
    output = tool.run("cat", timeout=5)
    assert "killed by timeout" not in output


def test_run_clamps_timeout_to_foreground_cap():
    output = tool.run("echo hi", timeout=tool.MAX_FOREGROUND_TIMEOUT + 100)
    assert "hi" in output


def test_schema_has_required_command_param():
    function = tool.SCHEMA["function"]
    assert function["name"] == "Shell"
    assert function["parameters"]["required"] == ["command"]


def test_step_1_bash_kimi_module_imports():
    assert callable(chat)
    assert callable(step)
    assert callable(turn)
