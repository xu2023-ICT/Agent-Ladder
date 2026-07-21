# Agent Instructions

## Code Comments

Keep code comments and docstrings focused on the code's purpose, behavior, and non-obvious design constraints.

Do not put local environment details, private gateway URLs, one-off debugging findings, or machine-specific setup notes in code comments. Put operational notes in this file and project planning notes in `PLAN.md`.

## Running a Step's SWE-bench Pipeline

Two separate phases: generate predictions (calls the model, no Docker), then
evaluate them (runs each patch's tests in Docker, no model calls).

Docker (WSL2, systemd-enabled) should already be running once the distro is
open, since `docker` is enabled via systemd. Check first:

```bash
docker info >/dev/null 2>&1 && echo "docker OK" || sudo systemctl start docker
```

Step 0:

```bash
# 1. Generate predictions.jsonl (real API calls to qwen3-max, ~30-45 min for the 30-instance subset)
uv run python -m agent_ladder.steps.step_0_bare_chat.run

# 2. Evaluate predictions.jsonl in Docker (builds/reuses per-repo images, runs tests)
uv run python -m agent_ladder.benchmarks.swebench.evaluate \
    src/agent_ladder/steps/step_0_bare_chat/predictions.jsonl step-0
```

Both are slow (minutes to an hour+) — run them with `run_in_background` or
in a `tmux`/`screen` session, not in the foreground.

Per-instance results land in `logs/run_evaluation/<run_id>/qwen3-max/<instance_id>/report.json`
(has `"resolved": true/false` regardless of whether the final aggregate
`<run_id>.qwen3-max.json` summary got written). If the evaluate step errors
out at the very end (e.g. a transient network blip fetching a repo's
`requirements.txt` mid-run), the per-instance `report.json` files already
computed are still valid — no need to redo the whole run just because the
final summary step failed. Just re-run `evaluate` again; already-built
Docker image layers are reused, so retries are much faster than the first
run.

## GitHub Push

For this repository, do not use GitHub SSH on port 22. The local network closes that connection.

Use GitHub SSH over port 443 with the dedicated GitHub key:

```bash
git config url.ssh://git@ssh.github.com:443/.insteadOf git@github.com:
git config core.sshCommand 'ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'
git branch --set-upstream-to=origin/main main
```

After the config is present, normal commands should work:

```bash
git push
git pull
git fetch
```

If a one-off push command is needed, use:

```bash
GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519_github -p 443 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' \
  git push -u ssh://git@ssh.github.com/xu2023-ICT/Agent-Ladder.git main
```
