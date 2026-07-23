# Claude Code

`minicode` gives the model one `bash` tool: a brand-new `bash -c command` subprocess per call, `command`/`timeout` only, stdout+stderr merged, crude tail truncation, no cwd or env carried between calls. This variant is grounded in local `reference-agents/claude-code` (`packages/builtin-tools/src/tools/BashTool/`, `src/utils/bash/ShellSnapshot.ts`, `bootstrap/state.ts`, `src/utils/timeouts.ts`, `src/utils/shell/outputLimits.ts`, `src/query.ts`) and keeps Claude Code's most representative trade-off: still one fresh subprocess per call, but the working directory persists across calls anyway.

The schema (`tool/schema.py`) tells the model exactly that split up front:

```python
DESCRIPTION = (
    "Run a shell command and get back its output. This is the only tool "
    "available: use it for everything -- listing and reading files, "
    "searching, editing with sed/heredocs, running tests, and so on. Each "
    "call starts a fresh, non-interactive shell process -- environment "
    "variables, aliases, and shell functions do NOT persist between calls -- "
    "but the working directory does (a `cd` in one call affects the next)."
)
```

There's no live shell process sitting around remembering where it is -- `tool/handler.py` fakes it by appending a marker to the command, parsing the exit code and `$PWD` back out of stdout, and handing the new cwd to the next subprocess's `cwd=`:

```python
def _run_bash(command: str, cwd: str, timeout: float) -> tuple[str, str]:
    wrapped = (
        f"{command}\n"
        f"__al_exit=$?\n"
        f'printf "{_EXIT_MARKER}%s{_EXIT_MARKER}{_CWD_MARKER}%s{_CWD_MARKER}" "$__al_exit" "$PWD"\n'
    )
    result = subprocess.run(["bash", "-c", wrapped], cwd=cwd, ...)
    ...
```

```python
def run(command: str, state: BashState, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Run `command` in a fresh subprocess and update persistent cwd state."""
    output, next_cwd = _run_bash(command, state.cwd, timeout)
    state.cwd = next_cwd
    return output
```

`tool/state.py` is just `BashState(cwd: str)`, closed over by `run.py`'s `turn()` and threaded through every `step()` call. Real Claude Code does the same trick at the application layer, not inside a persistent shell: `bootstrap/state.ts`'s `setCwdState`/`getOriginalCwd` record cwd after each call, and `Shell.ts` reinjects it on the next spawn -- "cwd survives" is recorded-and-replayed on both sides, not remembered by a shell that's still alive. `ShellSnapshot.ts` is a different mechanism entirely (a one-time snapshot of the user's interactive shell env/aliases taken at session start, unrelated to cross-call cwd) and has no equivalent here.

Output formatting also diverges from minicode's merged stdout+stderr: stdout and stderr stay separate, and the exit code is always appended, not just on failure:

```python
parts = []
if stdout.strip():
    parts.append(_truncate(stdout.rstrip("\n")))
if result.stderr.strip():
    parts.append("stderr:\n" + _truncate(result.stderr.rstrip("\n")))
parts.append(f"exit code: {exit_code}")
```

`MAX_OUTPUT_CHARS = 30_000` (vs. minicode's `20_000`) matches real Claude Code's `BASH_MAX_OUTPUT_DEFAULT` in `src/utils/shell/outputLimits.ts` -- production can raise that to 150k and writes the untruncated output to a `rawOutputPath` the model can re-read; this variant only keeps the truncation, not the re-readable-file layer. Default timeout is `120` (vs. minicode's `60`), matching `src/utils/timeouts.ts`'s 2-minute default (overridable via `BASH_DEFAULT_TIMEOUT_MS`, hard-capped at 10 minutes); real Claude Code also has a 30-minute spawn-level backstop underneath that, collapsed into one timeout here.

The module split (`tool/schema.py`, `tool/state.py`, `tool/handler.py`) mirrors the real BashTool being its own package rather than a function embedded in a REPL loop. Left out as production hardening rather than Step-1 material: `run_in_background`, `dangerouslyDisableSandbox`, permission/sandbox checks, security validation, and concurrent tool-call batching.

This cwd-persistence sits between minicode/kimi-cli/opencode/qwen-code's fully-fresh shell (model must `cd` every time or chain with `&&`) and trae-agent's fully long-lived shell (risk of a stuck interactive program or polluted state poisoning every later call) -- closer to a user's terminal intuition without the hang risk. The loop's stop condition is unchanged from minicode: a response with no `tool_calls` is final. This matches real Claude Code's `queryLoop` (`src/query.ts`): any `tool_use` block sets `needsFollowUp = true`, and `!needsFollowUp` is the only exit; `runToolUse` (`toolExecution.ts`) wraps even tool exceptions into an `is_error: true` tool_result (`<tool_use_error>`-wrapped) fed back through the same path, not a separate exception branch -- this teaching version returns errors as plain tool-result text the same way. `MAX_STEPS = 50` is a hard backstop matching Claude Code's optional `maxTurns`.

## 怎么跑

打开这个变体的 TUI demo:

```bash
uv run python -m agent_ladder.steps.step_1_bash.claude_code.run
```

也可以直接在代码里调用 `turn`:

```python
from agent_ladder.steps.step_1_bash.claude_code.run import turn

messages = []
for event in turn(messages)("进入 /tmp 后打印当前目录,再运行 pwd 确认 cwd 是否保留"):
    print(event)
```

`turn(messages)` 会把用户消息追加到同一个 `messages` 列表里,并闭包持有 `tool.BashState`。TUI 中会看到 `ToolCallEvent` 和 `ToolResultEvent`;如果模型先调用 `bash` 执行 `cd /tmp`,下一次工具调用会从 `/tmp` 开始,但 `export FOO=bar` 这类环境变量不会跨调用保留。
