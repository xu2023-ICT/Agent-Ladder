"""Step 1 (qwen-code lineage): one universal `run_shell_command` tool,
wrapped in a standard tool-calling loop.

Step 0 could only talk. This adds the two things
`README.md` identifies as this chapter's real content: a single shell tool (`tool/`)
and a loop that, within one user turn, keeps calling the model, running
whatever tool calls it asks for, and feeding the results back -- until the
model replies without asking for another tool call. That "no tool calls
left in this reply" check is the entire stop condition; nothing else
decides when the loop ends, matching how qwen-code's own headless loop
(`nonInteractiveCli.ts`'s `while (true)`) and kimi-cli's agent loop both
work despite being independent implementations in different languages.

`chat` is step 0's primitive with the tool attached. `step` runs one model
call and executes any tool calls it made, appending the assistant message
and each tool result (`role: "tool"`) back into the conversation -- a fresh
message, not text stitched onto the assistant's own turn, so the next
`chat` call sees "here is what that command printed" as its own turn in the
history. `turn` is the outer loop, with a hard `MAX_STEPS` cap so a model
that never stops calling tools can't hang the demo forever.
"""

import json

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent
from agent_ladder.steps.step_1_bash.qwen_code import tool as shell_tool

MAX_STEPS = 20  # hard safety valve against an infinite tool-call loop


def chat(messages: list[dict]):
    return complete(messages=messages, tools=[shell_tool.SCHEMA], max_tokens=8192, timeout=180)


def step(messages: list[dict]):
    """Run one model call and dispatch every tool call it made.

    Appends the assistant's reply to `messages` (tool calls included, if
    any), then one `role: "tool"` message per call so the next `step` can
    see what each command actually printed. Returns the assistant message
    plus the (call, output) pairs so the caller can render what just
    happened.
    """
    message = chat(messages).choices[0].message

    assistant_message = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        assistant_message["tool_calls"] = [tc.model_dump(exclude_none=True) for tc in message.tool_calls]
    messages.append(assistant_message)

    results = []
    for call in message.tool_calls or []:
        args = json.loads(call.function.arguments)
        output = shell_tool.run(**args)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        results.append((call, output))

    return message, results


def turn(messages: list[dict]):
    """Adapt the tool-calling loop to the terminal demo's event stream.

    `messages` is the running conversation, appended to in place across
    turns (see step 0's `turn` for why this matters -- otherwise every
    reply would be answered with no memory of what came before). Within a
    single user turn, keep calling `step` until the model responds without
    any tool calls -- its own decision to stop, not an externally imposed
    "say DONE" convention.
    """

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_STEPS):
            message, results = step(messages)

            if message.content:
                yield TextEvent(message.content)

            if not results:
                return  # model made no tool calls this step -- it's done

            for call, output in results:
                yield ToolCallEvent(call.function.name, json.loads(call.function.arguments))
                yield ToolResultEvent(output)

        yield TextEvent(f"(stopped after {MAX_STEPS} tool-calling steps without a final reply)")

    return _turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
