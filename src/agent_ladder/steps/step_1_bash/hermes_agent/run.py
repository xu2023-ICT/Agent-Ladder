"""Step 1: one universal `terminal` tool, wrapped in a standard tool-calling loop.

Step 0 could only talk. This step gives the model a single way to act -- run
a shell command -- and a loop that lets it call that tool repeatedly within
one user turn: call terminal, read the result, decide whether to call it
again or answer, until it stops calling tools on its own. No dedicated
edit/read/search tools yet -- those are later chapters' job. No SWE-bench
harness here either; see AGENTS.md for where that plumbing lives.

Design grounded directly in hermes-agent's real terminal tool
(`reference-agents/hermes-agent/tools/terminal_tool.py` +
`tools/environments/local.py`, read from the local checkout, no web
search), not guessed:

- **Tool name and framing.** hermes-agent calls it `terminal`, and its
  description opens with "Filesystem, current working directory, and
  exported environment variables persist between calls" -- unlike agents
  whose bash-equivalent tool starts every call from a blank slate and
  requires the model to `cd`/chain commands with `&&` because nothing
  carries over. This step follows hermes-agent's choice: state persists.
- **How that persistence is actually implemented.** hermes-agent does NOT
  keep one long-lived shell process alive per session --
  `tools/environments/local.py`'s own docstring says "Spawn-per-call: every
  execute() spawns a fresh bash process." It fakes persistence with two
  file-based tricks instead: (1) an `export -p` environment snapshot is
  written after each command and sourced before the next one, so exported
  variables survive despite each call being a brand new process; (2) the
  wrapped command prints `pwd` after running, and the parsed value becomes
  the *next* call's cwd, so `cd` appears to persist too. The files under
  `tool/environments/` are a minimal version of exactly that trick.
- **Loop shape.** Call the model; if the response has no tool calls, that
  IS the final reply (hermes-agent's own loop literally comments
  `# No tool calls - this is the final response` at that branch,
  `agent/conversation_loop.py`); otherwise run every tool call, append one
  tool-result message per call, and loop. hermes-agent adds a hard
  `max_iterations` ceiling for the same reason `MAX_STEPS` exists here: a
  model that never stops calling tools must not hang the turn forever.

What's deliberately left out, because it's production hardening rather than
part of what "terminal tool + tool-calling loop" teaches: background
processes/`notify_on_complete`, PTY mode, Docker/SSH/Modal sandboxing,
per-command approval gating, and the dangerous-command/sudo handling that
make up most of the real 3000+ line file.
"""

import json
from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent

from .tool import SCHEMA, TerminalTool

MAX_STEPS = 20  # hard safety valve against an infinite tool-call loop


def chat(messages: list[dict]):
    return complete(messages=messages, tools=[SCHEMA], max_tokens=8192, timeout=180)


def step(messages: list[dict], terminal: TerminalTool):
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
        output = terminal.run(**args)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        results.append((call, output))

    return message, results


def turn(messages: list[dict]):
    """Adapt the tool-calling loop to the terminal demo's event stream.

    `messages` is the running conversation, appended to in place across
    turns (see step 0's `turn` for why). `terminal` is created once here and
    closes over every `_turn` call, so cwd/exported-env state persists not
    just within one turn's tool-calling loop but across turns too -- exactly
    what "persist between calls" means in hermes-agent's tool description.
    """
    terminal = TerminalTool()

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_STEPS):
            message, results = step(messages, terminal)

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
