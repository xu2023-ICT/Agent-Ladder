"""Step 1, opencode variant: one universal `bash` tool + a tool-calling loop.

Same chapter as step 1's other reference-agent variants under `steps/` --
one all-purpose shell tool, no dedicated edit/read/search tools yet, wrapped
in a loop that keeps calling the model until it replies without a tool call.
This variant is grounded in opencode's real implementation
(`reference-agents/opencode/packages/opencode/src/`, read directly, no web
search; see `README.md` for the
full writeup) rather than guessed:

- **Loop shape.** opencode's `session/prompt.ts` `runLoop()` is a hand-written
  `while (true)` that calls the model once per iteration and stops exactly
  when the last step's response carries no more tool calls -- it deliberately
  does NOT use the AI SDK's built-in multi-step agent loop (no `stopWhen`/
  `maxSteps` passed to `streamText`, `session/llm.ts:280-324`), because the
  app needs to hook persistence/permissions/compaction into every single
  step. `step`/`turn` below are that same two-layer shape: `step` is one
  model call + dispatching whatever tool calls it made (opencode's
  `streamText` call, which auto-executes tool calls within one step);
  `turn` is the outer loop that keeps calling `step` until a step comes back
  with no tool calls to dispatch.
- **Stop condition.** "the last response had zero tool calls" reuses the
  provider's own `tool_calls`/`finish_reason` semantics rather than an
  ad-hoc convention like a magic string -- exactly opencode's `finish !==
  "tool-calls"` check (`session/prompt.ts:1111-1116`).
- **Max-steps safety valve.** opencode's default is actually *no* cap
  (`agent.steps ?? Infinity`) and, when one is configured, enforces it by
  injecting a soft "please stop calling tools" prompt rather than a hard
  break (`packages/core/src/session/runner/max-steps.ts`). `MAX_STEPS`
  below is a hard break instead -- simpler to reason about for a teaching
  demo, and closer to how the other variants guard against a runaway loop.

The `bash` tool itself (`tool/`) is opencode's `command` (required) +
`timeout` (optional, defaulted) parameter pair with `workdir` left out --
see `tool/bash.py`'s docstring for why.
"""

import json

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent

from . import tool as bash_tool

MAX_STEPS = 20  # hard safety valve against an infinite tool-call loop


def chat(messages: list[dict]):
    return complete(
        messages=messages,
        tools=[bash_tool.SCHEMA],
        max_tokens=8192,
        timeout=180,
    )


def step(messages: list[dict]):
    """Run one model turn and dispatch any tool calls it made.

    Appends the assistant's reply to `messages` (with tool calls, if any),
    then appends one tool-result message per call so the next `step` sees
    what each command actually printed. Returns the assistant message plus
    the (call, output) pairs so the caller can render what just happened.
    """
    message = chat(messages).choices[0].message
    messages.append(message.model_dump(exclude_none=True))

    results = []
    for call in message.tool_calls or []:
        args = json.loads(call.function.arguments)
        output = bash_tool.run(**args)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        results.append((call, output))

    return message, results


def turn(messages: list[dict]):
    """Adapt the tool-calling loop to the terminal demo's event stream.

    `messages` is the running conversation, appended to in place across
    turns (see step 0's `turn` for why). Within a single user turn, this
    keeps calling `step` and feeding tool results back until the model
    responds without calling `bash` again -- the "standard tool-calling
    loop" this chapter adds on top of step 0's single completion call.
    """

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_STEPS):
            message, results = step(messages)

            if message.content:
                yield TextEvent(message.content)

            if not results:
                return

            for call, output in results:
                yield ToolCallEvent(call.function.name, json.loads(call.function.arguments))
                yield ToolResultEvent(output)

        yield TextEvent(f"(stopped after {MAX_STEPS} tool-calling steps without a final reply)")

    return _turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
