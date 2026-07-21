import pytest

from agent_ladder.shared.llm import complete


@pytest.mark.integration
def test_complete_reaches_gateway():
    resp = complete(
        messages=[{"role": "user", "content": "reply with exactly: ok"}],
        max_tokens=20,
        timeout=30,
    )
    assert resp.choices[0].message.content
