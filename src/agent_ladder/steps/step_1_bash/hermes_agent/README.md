# Hermes Agent

`minicode`'s tool is called `bash`, states plainly that nothing persists between calls, and requires the model to chain everything with `&&`/`;`. This variant is grounded in local `reference-agents/hermes-agent` (`tools/terminal_tool.py`, `tools/environments/local.py`, `agent/conversation_loop.py`) and follows its actual design: a tool named `terminal` whose description claims the opposite of minicode's --

```python
DESCRIPTION = (
    "Execute a shell command. Filesystem, current working directory, and "
    "exported environment variables persist between calls -- if you `cd` "
    "somewhere or `export` a variable in one call, it is still in effect on "
    "the next call, so there is no need to re-`cd` or re-export on every "
    "call. ..."
)
```

Real hermes-agent does **not** back that claim with one long-lived shell process -- its own `tools/environments/local.py` docstring says "Spawn-per-call: every execute() spawns a fresh bash process." It fakes persistence with a file-based trick instead, reproduced in `tool/environments/base.py`'s `_wrap_command`: source an env snapshot file before the command, run the command, `export -p` a fresh snapshot after, and print a `pwd` marker:

```python
def _wrap_command(self, command: str) -> str:
    return (
        f"source {self._snapshot_path} 2>/dev/null\n"
        f"{command}\n"
        "__agent_ladder_exit=$?\n"
        f"export -p > {self._snapshot_path} 2>/dev/null\n"
        f"printf '\\n{_CWD_MARKER}%s{_CWD_MARKER}\\n' \"$(pwd)\"\n"
        "exit $__agent_ladder_exit\n"
    )
```

`execute()` then parses that marker back out and updates `self.cwd` for the *next* subprocess's `cwd=` -- the same recorded-and-replayed pattern the Claude Code variant uses for cwd alone, except here it also covers `export`ed variables via the snapshot file:

```python
def execute(self, command: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    wrapped = self._wrap_command(command)
    output, exit_code, timed_out = self._run_bash(wrapped, timeout=timeout)
    output, new_cwd = self._extract_cwd(output)
    if new_cwd and os.path.isdir(new_cwd):
        self.cwd = new_cwd
    ...
```

So `cd` and `export` both appear to survive across calls, but aliases, shell functions, unexported variables, and actual process state (background jobs, etc.) do not -- and there's a known edge case shared with the real wrapper: if the user's command itself calls `exit` at the top level, the snapshot/cwd-marker lines after it never run.

Schema shape is otherwise the same as minicode's (`command` + optional `timeout`), just with a longer default timeout (`180`s vs. minicode's `60`s) and `MAX_OUTPUT_CHARS` at the same `20_000` -- the truncation *message* differs cosmetically (`"...[truncated, N more chars]"` vs. minicode's `"[...truncated]"`), and a timeout appends `"Command timed out after {timeout}s."` after whatever output was already captured, rather than discarding it. `TerminalTool.cleanup()` removes the temporary snapshot file, a resource minicode's stateless subprocess model never needed.

Module split (`tool/terminal_tool.py` for schema + facade, `tool/environments/base.py` for the wrap/marker logic, `tool/environments/local.py` for the actual `bash -c` executor) mirrors real hermes-agent's `tools/terminal_tool.py` + `tools/environments/*` split.

This sits between two extremes: minicode/Codex's fully-fresh shell (nothing persists, model must `cd`/`export` every call) and trae-agent's fully long-lived shell (real persistence, but one stuck interactive program or a polluted shell state can wreck every later call). It's more usable than the former -- the model can `cd` once and keep working there, `export` once and keep reading the value -- without the hang risk of the latter, since every call is still a disposable subprocess.

Loop shape matches hermes-agent's `agent/conversation_loop.py`, which literally comments `# No tool calls - this is the final response` at the branch this step's `turn()` mirrors: no tool calls ends the turn, tool calls get executed and their results appended as one `role: "tool"` message each before looping again. `MAX_STEPS = 20` is the same kind of hard ceiling as hermes-agent's own iteration budget, not a change in the actual stop condition -- the model still stops by simply not calling the tool again, never by a magic string.

What's left out, because it's production hardening rather than what "one terminal tool + persistence trick" teaches here: Docker/SSH/Modal/Singularity/Daytona backends, background tasks and notifications, PTY mode, sudo/dangerous-command handling, per-command approval, and environment-config syncing.

## 怎么跑

打开这个变体的 TUI demo:

```bash
uv run python -m agent_ladder.steps.step_1_bash.hermes_agent.run
```

也可以直接在代码里调用 `turn`:

```python
from agent_ladder.steps.step_1_bash.hermes_agent.run import turn

messages = []
for event in turn(messages)("cd /tmp 并 export X=ok,然后再运行 pwd 和 printf $X 验证状态"):
    print(event)
```

`turn(messages)` 会创建一个 `TerminalTool` 并在多轮用户输入之间复用它,所以 cwd 和 exported env 不只在单轮 tool-calling loop 内保留,也会在这个 TUI 会话的后续用户轮次中保留。用完底层工具时可调用 `TerminalTool.cleanup()` 删除临时 env snapshot 文件;TUI demo 的短生命周期里这只是一个小的清理细节。
