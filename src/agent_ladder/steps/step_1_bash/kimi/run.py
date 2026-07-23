"""Step 1 (kimi-cli lineage): one universal `Shell` tool + a tool-calling loop.

Step 0 could only talk. This adds exactly the two things
`README.md` identifies as this chapter's
real content, grounded in reading kimi-cli's actual source
(`reference-agents/kimi-cli`) rather than guessing:

- A single shell tool (`tool/`, kimi-cli's `Shell`) -- no dedicated
  read/edit/search tools yet, ls/cat/grep/sed/running tests/editing via
  heredoc all go through it.
- A loop that, within one user turn, keeps calling the model and dispatching
  whatever tool calls it made, feeding the results back, until a step comes
  back with zero tool calls -- the model's own decision to give a final
  reply, not an ad-hoc "the model said DONE" convention.

kimi-cli itself builds this loop in three layers (`kosong.generate` -> one
LLM call; `kosong.step` -> that call plus dispatching its tool calls;
`KimiSoul._agent_loop`/`_step`, `soul/kimisoul.py:937-1346` -> the actual
`while True` that keeps going until a step's `StepOutcome.stop_reason` is
`"no_tool_calls"`). `chat`/`step`/`turn` below collapse that into the two
layers this step needs to teach: `step` is kosong's `generate()` + `step()`
combined -- one model call plus running every tool call it returned; `turn`
is `_agent_loop`'s `while True` with its engineering hardening (approval,
compaction, D-Mail, dedup, `MaxStepsReached`) stripped down to the one
safety valve that matters here: a hard `MAX_STEPS` cap so a model that never
stops calling tools can't hang the demo forever, playing the same role as
kimi-cli's own `max_steps_per_turn`.
"""

import json

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent
from agent_ladder.steps.step_1_bash.kimi import tool as shell_tool

MAX_STEPS = 20  # hard cap on tool-calling rounds within one user turn -- kimi-cli's max_steps_per_turn


def chat(messages: list[dict]):
    return complete(messages=messages, tools=[shell_tool.SCHEMA], max_tokens=8192, timeout=180)


def step(messages: list[dict]):
    """Run one model call and dispatch every tool call it made.

    Appends the assistant's reply to `messages` (tool calls included, if
    any), then one `role: "tool"` message per call so the next `step` sees
    what each command actually printed -- kimi-cli's `_grow_context`
    (`kimisoul.py:1389-1409`) appending the assistant message and each tool
    result back into history. Returns the assistant message plus the (call,
    args, output) triples; an empty list is the loop's stop signal.
    """
    message = chat(messages).choices[0].message
    messages.append(message.model_dump(exclude_none=True))

    results = []
    for call in message.tool_calls or []:
        args = json.loads(call.function.arguments or "{}")
        output = shell_tool.run(**args)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        results.append((call, args, output))

    return message, results


def turn(messages: list[dict]):
    """Adapt the tool-calling loop to the terminal demo's event stream.

    `messages` is the running conversation, appended to in place across
    turns (see step 0's `turn` for why). Within a single user turn, this
    keeps calling `step` and feeding tool results back until the model
    responds without calling `Shell` again -- the same core branch as
    kimi-cli's `_agent_loop` (`if result.tool_calls: continue` else stop),
    with everything else in that loop (approval, plan mode, compaction,
    hooks) left out as noise that isn't this chapter's teaching point.
    """

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
