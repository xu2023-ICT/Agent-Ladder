# Codex

`minicode`'s `bash` tool takes only `command`/`timeout`, runs a plain `bash -c`, and has no notion of directory at all -- every call inherits whatever cwd the harness process happened to start in. This variant is grounded in local `reference-agents/codex` Rust source -- `codex-rs/core/src/tools/handlers/shell_spec.rs`, `codex-rs/core/src/tools/handlers/shell/shell_command.rs`, and `codex-rs/core/src/shell.rs` -- and implements Codex's smaller `shell_command` tool (not the newer PTY-based `exec_command`), whose schema adds an explicit `workdir` parameter:

```python
"properties": {
    "command": {"type": "string", "description": "The shell script to execute in the user's default shell."},
    "workdir": {"type": "string", "description": "Working directory to run the command in; defaults to the process cwd."},
    "timeout": {"type": "number", "description": f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT_SECONDS}."},
},
"required": ["command"],
```

The description makes the trade-off explicit -- state isn't remembered anywhere, so the model must pass `workdir` on every call instead of relying on a previous `cd`:

```python
DESCRIPTION = (
    "... Always set the `workdir` param instead of `cd`-ing inside the command: "
    "each call is a fresh, non-interactive login shell, so nothing persists "
    "between calls (no cwd, no env vars, no shell history) -- chain related "
    "commands in one call with `&&`/`;`/`|` instead of relying on state left "
    "over from a previous call."
)
```

Execution differs too: a *login* shell (`bash -lc`, matching `derive_exec_args` in `core/src/shell.rs`) instead of minicode's plain `bash -c`, so `PATH` and shell init files match a real terminal more closely than a bare non-interactive shell would:

```python
def derive_exec_args(command: str, login: bool = True) -> list[str]:
    arg = "-lc" if login else "-c"
    return ["bash", arg, command]
```

`workdir` flows straight into `subprocess.run(cwd=workdir)` (`tool/shell.py`), and `tool/handler.py` catches an invalid path as a plain `OSError` instead of letting the exception escape:

```python
except OSError as exc:
    duration = time.monotonic() - start
    return _format(str(exc), 1, duration, False)
```

Output formatting also diverges from minicode's "(exit code: N)" tail: Codex-style output is an execution summary with exit code and wall time up front, and truncation keeps head *and* tail while dropping the middle (minicode only keeps the head):

```python
def _truncate_middle(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    keep = max_chars // 2
    omitted = len(text) - 2 * keep
    return f"{text[:keep]}\n... [{omitted} chars omitted] ...\n{text[-keep:]}"
```

Head often carries command context or a file's opening lines; tail carries the final error and exit status -- both matter more than the middle. A timeout doesn't just report failure, either: it returns whatever partial output the process had already produced by the time it was killed, formatted the same way as a normal result.

Module split mirrors Codex's own layering: `tool/schema.py` ~ `shell_spec.rs` (name/description/params), `tool/shell.py` ~ `core/src/shell.rs`'s `derive_exec_args`, `tool/handler.py` ~ `shell/shell_command.rs` (execution, timeout/OSError handling, model-facing formatting); `tool/shell_command.py` is only a compat re-export.

This is the variant to look at for Codex's interface-boundary style: state isn't hidden in a shell, it's threaded through explicit parameters on every call. That makes behavior predictable -- no call is polluted by a previous one's cwd/env/alias -- at the cost of requiring the model to remember to pass `workdir`, or it'll keep reading/testing in the wrong directory. Compare to the Claude Code and Hermes variants, which trade that predictability for a more terminal-like feel.

The loop stop condition is the same "no tool_calls -> final reply" shape as minicode, described in Codex terms as `needs_follow_up`: any tool call in the response means the model isn't done and must see the results before deciding what's next. `run.py` runs tool calls one at a time in call order; real Codex can process concurrent tool calls through a `FuturesOrdered` queue, but sequential execution is simpler to read and this step only ever has one shell tool anyway.

## 怎么跑

打开这个变体的 TUI demo:

```bash
uv run python -m agent_ladder.steps.step_1_bash.codex.run
```

也可以直接在代码里调用 `turn`:

```python
from agent_ladder.steps.step_1_bash.codex.run import turn

messages = []
for event in turn(messages)("在当前仓库里找 pyproject.toml,再读出项目名"):
    print(event)
```

如果不开模型,也可以只理解工具层行为:`tool.run(command="pwd", workdir="...")` 每次都会新开 shell,所以要靠 `workdir` 指定位置;连续两次调用之间不会继承上一次命令里的 `cd` 或 `export`。
