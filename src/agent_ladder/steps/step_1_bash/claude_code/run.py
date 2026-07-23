"""Step 1 Claude Code track: model loop plus TUI entry point."""

import json
import os

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent
from agent_ladder.steps.step_1_bash.claude_code import tool

MAX_STEPS = 50


def step(messages: list[dict], state: tool.BashState):
    """One model call, plus running any tool calls it asks for."""
    response = complete(messages=messages, tools=[tool.SCHEMA], max_tokens=8192, timeout=180)
    message = response.choices[0].message
    tool_calls = message.tool_calls or []

    assistant_message = {"role": "assistant", "content": message.content}
    if tool_calls:
        assistant_message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in tool_calls
        ]
    messages.append(assistant_message)

    events = []
    if message.content:
        events.append(TextEvent(message.content))
    if not tool_calls:
        return True, events

    for call in tool_calls:
        args = json.loads(call.function.arguments or "{}")
        events.append(ToolCallEvent(call.function.name, args))
        output = tool.run(args.get("command", ""), state, args.get("timeout", tool.DEFAULT_TIMEOUT))
        events.append(ToolResultEvent(output))
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

    return False, events


def chat(messages: list[dict], state: tool.BashState):
    """Run the tool-calling loop until the model stops calling the bash tool."""
    for _ in range(MAX_STEPS):
        done, events = step(messages, state)
        yield from events
        if done:
            return
    yield TextEvent(f"[stopped after {MAX_STEPS} steps without a final reply]")


def turn(messages: list[dict]):
    """Adapt `chat` to the terminal demo's event stream (see shared/tui.py)."""
    state = tool.BashState(cwd=os.getcwd())

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})
        yield from chat(messages, state)

    return _turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
