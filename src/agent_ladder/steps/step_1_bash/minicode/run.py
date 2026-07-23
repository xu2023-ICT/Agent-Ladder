"""Step 1, minicode baseline: one universal `bash` tool + a tool-calling loop.

Step 0 could only talk. This step gives the model exactly one way to act on
the world -- run a shell command -- wrapped in a loop that lets the model
call that tool repeatedly within a single user turn: call bash, read the
result, decide whether to call it again or answer, until it stops calling
tools on its own. No dedicated read/edit/search tools yet -- ls, cat, grep,
sed, running tests, editing via heredoc, all go through the one `bash` tool.

The design is grounded in reading real reference-agent implementations, not
guessing. kimi-cli and qwen-code, independently and in different languages,
converge on the same minimal shape this step follows: a single required
`command` parameter, a brand-new non-interactive subprocess per call with
nothing carried over between calls, stdout+stderr merged into one string
with the exit code appended on failure, and a loop that keeps calling the
model until a response comes back with zero tool calls -- the model's own
decision to give a final answer, not an ad-hoc "the model said DONE"
convention. This `minicode` folder is the generic, non-reference-specific
implementation of that shape -- see the sibling `claude_code/`, `codex/`,
`hermes_agent/`, `kimi/`, `opencode/`, `pi_mono/`, `qwen_code/`,
`trae_agent/` folders for how this compares against each real agent's own
design.
"""

import json

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent
from agent_ladder.steps.step_1_bash.minicode.tool import BASH_TOOL, run_bash

MAX_STEPS = 20  # hard cap on tool-calling rounds within one user turn


def chat(messages: list[dict]):
    return complete(messages=messages, tools=[BASH_TOOL], max_tokens=8192, timeout=180)


def step(messages: list[dict]):
    """Run one model call and execute whatever tool calls it makes."""
    message = chat(messages).choices[0].message
    messages.append(message.model_dump(exclude_none=True))

    results = []
    for call in message.tool_calls or []:
        args = json.loads(call.function.arguments or "{}")
        output = run_bash(**args)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        results.append((call, args, output))

    return message, results


def turn(messages: list[dict]):
    """Adapt the tool-calling loop to the terminal demo's event stream."""

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_STEPS):
            message, results = step(messages)

            if message.content:
                yield TextEvent(message.content)

            if not results:
                return

            for call, args, output in results:
                yield ToolCallEvent(call.function.name, args)
                yield ToolResultEvent(output)

        yield TextEvent(f"(stopped after {MAX_STEPS} tool-calling steps without a final reply)")

    return _turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
