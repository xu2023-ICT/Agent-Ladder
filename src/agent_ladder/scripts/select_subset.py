"""Pick the fixed 30-instance SWE-bench Lite subset, stratified across all 12 repos.

One-off script: run it once, commit the resulting instance-id list. Not meant
to be re-run except to deliberately change the subset (in which case bump
SEED or the target size and re-commit the output).

Run with: uv run python -m agent_ladder.scripts.select_subset
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from datasets import load_dataset

SEED = 42
TARGET_SIZE = 30
OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "benchmarks"
    / "swebench"
    / "swebench_lite_30.json"
)


def allocate_counts(repo_sizes: dict[str, int], target_size: int) -> dict[str, int]:
    """Largest-remainder apportionment, with every repo guaranteed >= 1 slot."""
    repos = sorted(repo_sizes)  # alphabetical for deterministic tie-breaks
    total = sum(repo_sizes.values())

    counts = {repo: 1 for repo in repos}
    remaining = target_size - len(repos)
    if remaining < 0:
        raise ValueError(f"target_size={target_size} is smaller than repo count={len(repos)}")

    exact = {repo: repo_sizes[repo] / total * target_size for repo in repos}
    fractional = {repo: exact[repo] - int(exact[repo]) for repo in repos}
    extra_floor = {repo: max(int(exact[repo]) - 1, 0) for repo in repos}
    for repo in repos:
        counts[repo] += extra_floor[repo]
    remaining -= sum(extra_floor.values())

    ranked = sorted(repos, key=lambda r: fractional[r], reverse=True)
    for repo in ranked[:remaining]:
        counts[repo] += 1

    return counts


def main():
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")

    by_repo = defaultdict(list)
    for row in ds:
        by_repo[row["repo"]].append(row["instance_id"])

    repo_sizes = {repo: len(ids) for repo, ids in by_repo.items()}
    counts = allocate_counts(repo_sizes, TARGET_SIZE)

    rng = random.Random(SEED)
    selected = []
    for repo in sorted(by_repo):
        pool = sorted(by_repo[repo])
        selected.extend(rng.sample(pool, counts[repo]))

    selected.sort()
    assert len(selected) == TARGET_SIZE, len(selected)

    OUTPUT_PATH.write_text(json.dumps(selected, indent=2) + "\n")

    print(f"repo sizes (of {len(ds)} total): {repo_sizes}")
    print(f"allocated counts (sum={sum(counts.values())}): {counts}")
    print(f"wrote {len(selected)} instance ids to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
