from agent_ladder.benchmarks.swebench.dataset import load_subset
from agent_ladder.benchmarks.swebench.repo import checkout
from agent_ladder.shared.llm import complete
from agent_ladder.steps.step_0_bare_chat.oracle import build_prompt


def test_reorganized_modules_import():
    assert callable(load_subset)
    assert callable(checkout)
    assert callable(complete)
    assert callable(build_prompt)
