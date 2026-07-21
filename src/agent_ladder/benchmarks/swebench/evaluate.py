"""Runs the official SWE-bench evaluation harness against a predictions file.

Requires Docker: each candidate patch runs inside a per-instance container to
check whether it actually resolves the issue (applies + the right tests
pass). Shared across steps -- every step scores its own predictions.jsonl
through this same entry point.

Run with: uv run python -m agent_ladder.benchmarks.swebench.evaluate <predictions_path> <run_id>
"""

import sys

from swebench.harness.run_evaluation import main as run_evaluation

DATASET_NAME = "princeton-nlp/SWE-bench_Lite"


def evaluate(predictions_path: str, run_id: str, report_dir: str = "."):
    run_evaluation(
        dataset_name=DATASET_NAME,
        split="test",
        instance_ids=None,
        predictions_path=predictions_path,
        max_workers=4,
        force_rebuild=False,
        cache_level="env",
        clean=False,
        open_file_limit=4096,
        run_id=run_id,
        timeout=1_800,
        namespace="swebench",
        rewrite_reports=False,
        modal=False,
        report_dir=report_dir,
    )


if __name__ == "__main__":
    predictions_path, run_id = sys.argv[1], sys.argv[2]
    evaluate(predictions_path, run_id)
