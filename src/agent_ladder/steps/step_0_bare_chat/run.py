"""Launch the Step 0 terminal demo."""

from agent_ladder.shared.tui import AgentChatApp
from agent_ladder.steps.step_0_bare_chat.chat import chat, turn


if __name__ == "__main__":
    AgentChatApp(turn([])).run()
