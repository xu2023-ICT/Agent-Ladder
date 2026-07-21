"""Loads the fixed 30-instance SWE-bench Lite subset used from step 1 onward.

The subset itself lives in swebench_lite_30.json, generated once by
agent_ladder.scripts.select_subset (stratified across all 12 repos, fixed seed).
"""

import json
from pathlib import Path

from datasets import load_dataset

SUBSET_PATH = Path(__file__).resolve().parent / "swebench_lite_30.json"


def load_subset():
    subset_ids = set(json.loads(SUBSET_PATH.read_text()))
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    return ds.filter(lambda row: row["instance_id"] in subset_ids)
