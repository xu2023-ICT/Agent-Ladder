from agent_ladder.benchmarks.swebench.dataset import load_subset
from agent_ladder.benchmarks.swebench.oracle import build_prompt
from agent_ladder.benchmarks.swebench.repo import checkout
from agent_ladder.benchmarks.swebench.step_0.run import solve
from agent_ladder.shared.llm import complete
from agent_ladder.steps.step_0_bare_chat.run import chat


def test_reorganized_modules_import():
    assert callable(load_subset)
    assert callable(checkout)
    assert callable(complete)
    assert callable(build_prompt)
    assert callable(chat)
    assert callable(solve)
