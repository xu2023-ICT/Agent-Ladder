"""Step 1: one universal `bash` tool + the standard tool-calling loop.

Step 0 was a single completion call -- no loop, no way to affect anything
outside the chat. This step adds both at once, because a tool is useless
without a loop that can call it more than once per user turn: the model
asks for a command, sees what it printed, and decides whether to run
another one or answer -- all inside a single user turn, before the reply
the user actually sees.

Design here follows pi-mono (reference-agents/pi-mono), a real, currently
maintained coding agent, read directly rather than guessed:

- Tool schema is just `command` (required) + `timeout` (optional seconds,
  no default) -- see packages/coding-agent/src/core/tools/bash.ts:40-43.
  No `cwd`, no `background`, no dedicated read/edit/search tools: ls, cat,
  grep, sed, running tests all go through this one tool, exactly as the
  chapter goal describes. Splitting those out is later chapters' job.
- Each call is a brand-new `bash -c command` subprocess (bash.ts:96-107)
  with stdout+stderr merged into one stream -- no persistent shell session,
  so nothing (cwd, env, background jobs) carries over between calls. The
  tool description says so explicitly, the same way pi-mono's does.
- A non-zero exit code or a timeout is treated as the command *failing*,
  not as ordinary output (bash.ts:397-424): the tool raises, carrying
  whatever output was captured. The loop -- not the tool -- is responsible
  for turning that into a normal tool-result message the model can react
  to, instead of letting the exception crash the run. This mirrors
  agent-loop.ts's executePreparedToolCall, which catches every
  tool.execute() throw and folds it into an `isError` tool result
  (agent-loop.ts:666-707).
- Long output is truncated to its *tail* (errors and final results are
  usually at the end), with the full output spilled to a temp file so the
  model can still go read the beginning if it needs to -- pi-mono's
  OutputAccumulator + truncate.ts does the same thing with a 2000-line/50KB
  limit; this step uses a single byte limit for simplicity.
- The loop's stop condition is just "did this turn's response include any
  tool calls" -- zero tool calls means the model chose to give its final
  reply. See agent-loop.ts:170-260 (`runLoop`): `hasMoreToolCalls` only
  stays true when the previous assistant message actually contained tool
  calls, so the `while` loop exits the moment the model replies without
  one. Notably, pi-mono imposes **no** artificial max-step cap here --
  the model is trusted to stop itself, and the real safety valve is the
  human aborting the run (Ctrl-C quits this demo's TUI too). This step
  follows that faithfully rather than adding a hardcoded step limit.
"""

import json

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent
from agent_ladder.steps.step_1_bash.pi_mono import tool as bash_tool


def _execute_tool_call(call) -> str:
    """Run one tool call through the pi-mono-style tool boundary.

    This is the loop-side half of pi-mono's error handling: agent-loop.ts's
    executePreparedToolCall wraps every tool.execute() call in a try/except
    and turns a thrown error into an `isError` tool-result message rather
    than letting it propagate and crash the run. Plain OpenAI-style tool
    messages have no separate error flag, so the tool package folds any
    BashError into result text and lets the model see the failure on the
    next turn.
    """
    args = json.loads(call.function.arguments or "{}")
    return bash_tool.execute_for_loop(args)


def chat(messages: list[dict]):
    return complete(messages=messages, tools=[bash_tool.SCHEMA], max_tokens=8192, timeout=180)


def turn(messages: list[dict]):
    """Adapt the bash tool + tool-calling loop to the terminal demo's event stream.

    `messages` is the running conversation, appended to in place across
    turns -- same reason as step 0: every turn, and every tool call/result
    inside it, must stay visible to the next completion call, or the model
    loses track of what it just ran and what came back.
    """

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})

        while True:
            message = chat(messages).choices[0].message
            messages.append(message.model_dump(exclude_none=True))

            if message.content:
                yield TextEvent(message.content)

            tool_calls = message.tool_calls or []
            if not tool_calls:
                return  # model chose not to call a tool -- turn is done

            for call in tool_calls:
                args = json.loads(call.function.arguments or "{}")
                yield ToolCallEvent(call.function.name, args)
                output = _execute_tool_call(call)
                yield ToolResultEvent(output)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
            # loop back: model sees the tool results, decides what's next

    return _turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
