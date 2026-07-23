from agent_ladder.steps.step_1_bash.minicode import run as base_run
from agent_ladder.steps.step_1_bash.minicode.run import BASH_TOOL, chat, run_bash, step, turn


def test_run_bash_merges_stdout_and_stderr():
    output = run_bash("echo out; echo err >&2")
    assert "out" in output
    assert "err" in output


def test_run_bash_reports_nonzero_exit_code():
    output = run_bash("exit 3")
    assert "exit code: 3" in output


def test_run_bash_kills_on_timeout():
    output = run_bash("sleep 5", timeout=1)
    assert "timed out" in output


def test_run_bash_does_not_hang_on_interactive_input():
    # stdin is closed, so a command reading from it hits EOF immediately
    # instead of blocking until the timeout.
    output = run_bash("cat", timeout=5)
    assert "timed out" not in output


def test_bash_tool_schema_has_required_command_param():
    function = BASH_TOOL["function"]
    assert function["name"] == "bash"
    assert function["parameters"]["required"] == ["command"]


def test_step_1_bash_module_imports():
    assert callable(chat)
    assert callable(step)
    assert callable(turn)


class FakeFunction:
    name = "bash"
    arguments = '{"command": "echo hi"}'


class FakeToolCall:
    id = "call_1"
    function = FakeFunction()

    def model_dump(self, exclude_none=False):
        assert exclude_none is True
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.function.name,
                "arguments": self.function.arguments,
            },
        }


class FakeMessage:
    content = None
    tool_calls = [FakeToolCall()]

    def model_dump(self, exclude_none=False):
        assert exclude_none is True
        return {
            "role": "assistant",
            "tool_calls": [call.model_dump(exclude_none=True) for call in self.tool_calls],
        }


class FakeChoice:
    message = FakeMessage()


class FakeResponse:
    choices = [FakeChoice()]


def test_step_appends_assistant_tool_call_and_tool_result_without_none_fields(monkeypatch):
    monkeypatch.setattr(base_run, "chat", lambda messages: FakeResponse())
    monkeypatch.setattr(base_run, "run_bash", lambda **kwargs: "hi")

    messages = [{"role": "user", "content": "say hi"}]
    message, results = base_run.step(messages)

    assert message is FakeChoice.message
    assert len(results) == 1
    assert messages == [
        {"role": "user", "content": "say hi"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": '{"command": "echo hi"}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "hi"},
    ]
