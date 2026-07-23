"""Step 1, trae-agent variant: one universal `bash` tool backed by a
persistent shell session, wrapped in the standard tool-calling loop.

Design choices below follow this folder's `README.md`,
reading trae-agent's real implementation rather than guessing:

- The bash tool here is a *persistent* `/bin/bash` process, reused across
  every call, instead of a fresh subprocess per call. This is what trae-agent's
  `bash_tool.py` actually does
  -- and its file header traces straight back to Anthropic's own
  computer-use reference implementation, so it's the closest thing to an
  "official" answer for what a universal bash tool should look like. cwd,
  environment variables and shell history all survive between calls; a
  `cd` in one tool call still applies to the next one.
- Command-boundary detection uses the same trick as the original, with one
  extra hardening tweak: every session gets a random sentinel, and after
  writing `command` the wrapper writes a `printf` trailer containing
  `sentinel + exit_code + sentinel`. The reader consumes raw bytes until
  that full trailer appears. Reading line-by-line would break whenever a
  command's last line of output has no trailing newline -- its output and
  the trailer would land on the same line and never match a line-prefix
  check.
- One deliberate correction to the original: trae-agent's `bash_tool.py`
  wraps every command in `(...)` before appending the sentinel echo (a
  subshell, used so `$?` reliably reflects the command's own exit status
  regardless of what it contains). That wrapping quietly breaks the "state
  is persistent across calls" claim in its own tool description --
  `cd`/shell variables set inside a subshell never reach the parent shell,
  so the *next* call would still see the old cwd. Confirmed by testing
  both versions directly against `bash`; this file drops the `(...)` so a
  `cd` in one call actually does apply to the next, which is the entire
  point of choosing a persistent session over a fresh subprocess per call.
- A hung command kills the whole session on a fixed timeout, and the
  session does not recover on its own -- the model has to pass
  `restart: true` before the shell can be used again. This mirrors
  trae-agent's own tradeoff: a persistent session buys cross-call state at
  the cost of a single wedged command taking the whole tool down until
  it's explicitly reset.
- One simplification from trae-agent's real code: stdout and stderr are
  merged into a single stream (`stderr=STDOUT`) rather than read from two
  separate pipes, to keep the synchronous implementation here simple and
  to match the merged-output shape the other two variants in this step
  already use. trae-agent's original keeps them apart because it runs on
  asyncio and can poll both buffers independently; that plumbing isn't
  needed to teach the persistent-session idea.
- The loop's stop condition is still "did this step's response include any
  tool calls" -- trae-agent's real stop condition is either a fragile
  substring match on the reply text (`BaseAgent.llm_indicates_task_completed`)
  or, in the subclass that actually ships, a dedicated `task_done` tool the
  model must remember to call. Neither is copied here: the tool-calling API
  already tells you when the model stopped calling tools, and that signal
  is what's used.
"""

import json

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import AgentChatApp, TextEvent, ToolCallEvent, ToolResultEvent

from .tool import BASH_TOOL, BashTool, ToolCall, ToolExecutor

MAX_STEPS = 20  # hard safety valve against an infinite tool-call loop
_executor = ToolExecutor([BashTool()])


def chat(messages: list[dict]):
    return complete(messages=messages, tools=[BASH_TOOL], max_tokens=8192, timeout=180)


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
        args = json.loads(call.function.arguments or "{}")
        result = _executor.execute_tool_call(
            ToolCall(name=call.function.name, call_id=call.id, id=call.id, arguments=args)
        )
        output = result.result or ""
        if result.error:
            output = f"{output}\n{result.error}".strip()
        output = f"{output}\nExit code: {result.error_code}"
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        results.append((call, output))

    return message, results


def turn(messages: list[dict]):
    """Adapt the tool-calling loop to the terminal demo's event stream.

    `messages` is the running conversation, appended to in place across
    turns (see step 0's `turn` for why). Within a single user turn, this
    keeps calling `step` and feeding tool results back until the model
    responds without calling `bash` again.
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
                yield ToolCallEvent(call.function.name, json.loads(call.function.arguments or "{}"))
                yield ToolResultEvent(output)

        yield TextEvent(f"(stopped after {MAX_STEPS} tool-calling steps without a final reply)")

    return _turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
