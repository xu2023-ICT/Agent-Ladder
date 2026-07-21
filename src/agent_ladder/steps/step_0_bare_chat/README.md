# Step 0 — bare chat

No agent loop, no tools. One `litellm.completion()` call per problem.

## What this step does

**Oracle mode**: for each SWE-bench instance, we hand the model the exact
files the reference (gold) patch touches, plus the issue text, and ask for a
unified diff in one shot. This is the original SWE-bench paper's (2023)
baseline methodology — there's no exploration, no test running, just "here
are the files that need to change, write the patch."

- `oracle.py` builds the prompt: checks out the repo at `base_commit`
  (via `agent_ladder.benchmarks.swebench.repo.checkout`), reads the
  gold-patch-touched files + any README, and assembles the same prompt
  template ("style-2") as the original paper.
- `run.py` runs this over the project's fixed 30-instance subset
  (`agent_ladder.benchmarks.swebench.dataset.load_subset`), calls
  `qwen3-max` through `agent_ladder.shared.llm.complete`, extracts the patch
  from the response, and writes `predictions.jsonl` in SWE-bench's
  prediction format (`instance_id`, `model_name_or_path`, `model_patch`).

## Run it

```bash
uv run python -m agent_ladder.steps.step_0_bare_chat.run
```

Writes `predictions.jsonl` next to this file. Each instance triggers one
repo checkout (cached under `.cache/swebench-repos/`, shared across steps)
and one real API call — expect it to take a few minutes and cost real
tokens.

## Score it

Scoring needs the official SWE-bench harness, which runs each candidate
patch inside a per-instance Docker container to check whether it actually
resolves the issue (applies + makes the right tests pass). Requires Docker.

```bash
uv run python -m agent_ladder.benchmarks.swebench.evaluate \
    src/agent_ladder/steps/step_0_bare_chat/predictions.jsonl step-0
```

That's a thin wrapper (`agent_ladder.benchmarks.swebench.evaluate`) around
`swebench.harness.run_evaluation` with this project's defaults baked in —
every step scores through the same entry point. It only evaluates whatever
instances are present in the predictions file, which is already just our 30.

Reports land in `./step-0.<model>.json`.

## Known limitations (expected, not bugs)

- Oracle mode is a different capability from what step 1 onward tests
  (agent self-directed exploration). The score curve can go *down* between
  step 0 and step 1 — that's expected, not a regression.
- The generated patch is often close but not clean unified-diff output
  (wrong hunk line counts, missing context lines). Fixing this is exactly
  what step 2's dedicated `edit` tool is for.
