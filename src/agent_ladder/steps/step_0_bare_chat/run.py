"""Step 0: pure chat, no loop, no tools.

Oracle mode -- hand the model the files the reference patch touches and ask
for a diff in one shot. This is the original SWE-bench paper's (2023)
baseline methodology, used here as the score curve's starting point.

Run with: uv run python -m agent_ladder.steps.step_0_bare_chat.run
"""

import json
from pathlib import Path

from swebench.inference.make_datasets.utils import extract_diff, extract_minimal_patch

from agent_ladder.benchmarks.swebench.dataset import load_subset
from agent_ladder.shared.llm import complete
from agent_ladder.steps.step_0_bare_chat.oracle import build_prompt

OUTPUT_PATH = Path(__file__).resolve().parent / "predictions.jsonl"
MODEL_NAME = "qwen3-max"


def solve(instance: dict) -> str:
    prompt = build_prompt(instance)
    resp = complete(
        messages=[{"role": "user", "content": prompt}],
        model=MODEL_NAME,
        max_tokens=8192,
        timeout=180,
    )
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
                "model_name_or_path": MODEL_NAME,
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
