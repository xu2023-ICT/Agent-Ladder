"""Step 1 (codex track): the bash tool + a tool-calling loop.

Step 0 was one completion call per turn -- the model could talk, but
couldn't look at or change anything outside the chat. This adds exactly one
capability: a `shell_command` tool (see `tool/`, grounded in codex's
`shell_command`/`exec_command` tool) and the loop that lets the model call it
repeatedly *within a single user turn* before replying. Codex's own turn loop
(`core/src/session/turn.rs::run_turn` / `try_run_sampling_request`) is
exactly this shape once the streaming/hooks/telemetry are stripped away:

    loop:
        response = model(history)
        if response has tool_calls:
            run each tool call, append its result to history
            continue                    # ask the model again
        else:
            return response.content     # model decided it's done

`needs_follow_up` in codex is just "did this response contain tool calls" --
tool calls mean the model isn't done yet and must see their results before
it can decide what's next; no tool calls means the model already gave its
final answer. Unlike codex, which executes concurrent tool calls through a
`FuturesOrdered` queue, this step runs tool calls one at a time in the order
the model issued them -- simpler to read, and a single turn rarely asks for
more than one shell command at once anyway.

Running it over a benchmark subset, extracting a patch, writing predictions,
scoring: all of that is harness plumbing, not part of what this step
teaches, so it doesn't live here.
"""

import json

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent
from agent_ladder.steps.step_1_bash.codex import tool


def chat(messages: list[dict]):
    return complete(messages=messages, tools=[tool.SCHEMA], max_tokens=8192, timeout=180)


def turn(messages: list[dict]):
    """Adapt the tool-calling loop to the terminal demo's event stream.

    Same running-history contract as step 0's `turn` (`messages` is appended
    to in place so every turn -- and every round of tool calls inside a
    turn -- sees everything said before it), plus the loop that lets one
    user message trigger several rounds of tool calls before the model
    settles on a final reply.
    """

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})

        while True:
            message = chat(messages).choices[0].message
            messages.append(message.model_dump(exclude_none=True))

            tool_calls = message.tool_calls or []
            if not tool_calls:
                yield TextEvent(message.content or "")
                return

            if message.content:
                yield TextEvent(message.content)

            for call in tool_calls:
                args = json.loads(call.function.arguments)
                yield ToolCallEvent(call.function.name, args)
                output = tool.run(
                    command=args["command"],
                    workdir=args.get("workdir"),
                    timeout=args.get("timeout", tool.DEFAULT_TIMEOUT_SECONDS),
                )
                yield ToolResultEvent(output)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": output,
                    }
                )

    return _turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
