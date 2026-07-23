"""Harness for step 0: runs the bare-chat step over the fixed 30-instance
subset in Oracle mode and writes predictions.jsonl for the evaluation
harness.

Run with: uv run python -m agent_ladder.benchmarks.swebench.step_0.run
"""

import json
from pathlib import Path

from swebench.inference.make_datasets.utils import extract_diff, extract_minimal_patch

from agent_ladder.benchmarks.swebench.dataset import load_subset
from agent_ladder.benchmarks.swebench.oracle import build_prompt
from agent_ladder.shared.llm import DEFAULT_MODEL
from agent_ladder.steps.step_0_bare_chat.chat import chat

OUTPUT_PATH = Path(__file__).resolve().parent / "predictions.jsonl"


def solve(instance: dict) -> str:
    messages = [{"role": "user", "content": build_prompt(instance)}]
    resp = chat(messages)
    raw = resp.choices[0].message.content or ""
    return extract_minimal_patch(extract_diff(raw))


def main():
    subset = load_subset()
    predictions = []
    for instance in subset:
        instance_id = instance["instance_id"]
        print(f"[{instance_id}] solving...")
        patch = solve(instance)
        predictions.append(
            {
                "instance_id": instance_id,
                "model_name_or_path": DEFAULT_MODEL,
                "model_patch": patch,
            }
        )
        print(f"[{instance_id}] patch length={len(patch)}")

    with open(OUTPUT_PATH, "w") as f:
        for pred in predictions:
            f.write(json.dumps(pred) + "\n")
    print(f"wrote {len(predictions)} predictions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
