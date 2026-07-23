"""Step 0: pure chat, no loop, no tools.

No agent loop deciding what to do next, no tools -- but it's still a real
chat: every turn sees the whole conversation so far, not just the latest
message. `chat` is the bare primitive (messages in, one completion call,
reply out); `turn` is what keeps a running conversation across turns.

Running it over a benchmark subset, extracting a patch, writing
predictions, scoring: all of that is harness plumbing, not part of what
"bare chat" teaches, so it lives under
agent_ladder.benchmarks.swebench.step_0 instead.
"""

from agent_ladder.shared.llm import complete
from agent_ladder.shared.tui import TextEvent


def chat(messages: list[dict]):
    return complete(messages=messages, max_tokens=8192, timeout=180)


def turn(messages: list[dict]):
    """Adapt `chat` to the terminal demo's event stream (see shared/tui.py).

    `messages` is the running conversation, appended to in place so each
    turn sees everything said before it -- otherwise every reply would be
    answered with no memory of what came before, which isn't "chat".
    """

    def _turn(user_text: str):
        messages.append({"role": "user", "content": user_text})
        reply = chat(messages).choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        yield TextEvent(reply)

    return _turn
