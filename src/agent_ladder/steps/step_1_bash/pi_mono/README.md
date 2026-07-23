# pi-mono

这个目录按 [pi-mono](https://github.com/earendil-works/pi-mono)(`packages/coding-agent`,一个真实、仍在维护的 coding agent)的实现路线展示 Step 1。骨架和 `minicode/` 同构——一个 `bash` 工具、一个 tool-calling 循环——差异集中在两处:遇到失败时工具和循环各自的责任划分,以及循环完全没有硬性的步数上限。

参数面比 minicode 还窄一点:`timeout` 没有默认值。`tool/schema.py`:

```python
SCHEMA = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Execute a bash command in the current working directory. Returns "
            "stdout and stderr combined. Output longer than a few KB is "
            "truncated to the tail (full output saved to a temp file, path "
            "included). Optionally provide a timeout in seconds. ..."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Bash command to execute"},
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional, no default timeout)",
                },
            },
            "required": ["command"],
        },
    },
}
```

对应 pi-mono 真实的 `packages/coding-agent/src/core/tools/bash.ts:40-43`。没有 `cwd`、没有 `background`,同样没有专用的 read/edit/search 工具——ls、cat、grep、sed、跑测试全走这一个工具。

第一处关键差异是失败语义:非零退出码或 timeout 在这里是真的**抛异常**,不是拼进返回字符串。`tool/errors.py` 定义了 `BashError`,`tool/executor.py` 的 `run_bash()` 直接 `raise`:

```python
def run_bash(command: str, timeout: float | None = None) -> str:
    accumulator = OutputAccumulator()
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        accumulator.append(exc.output or "")
        output = accumulator.snapshot(persist_if_truncated=True)
        raise BashError(f"Command timed out after {timeout} seconds", output) from exc

    accumulator.append(result.stdout or "")
    output = accumulator.snapshot(persist_if_truncated=True)
    if result.returncode != 0:
        raise BashError(f"Command exited with code {result.returncode}", output)
    return output
```

这对应真实 `bash.ts:397-424` 的行为。但异常不能就这样传给模型——OpenAI 风格的 tool message 没有单独的错误标志位。真正接住它的是循环这一侧,`tool/bash.py` 的 `execute_for_loop()`:

```python
def execute_for_loop(args: dict) -> str:
    try:
        return run(args.get("command", ""), timeout=args.get("timeout"))
    except BashError as exc:
        return f"{exc.output}\n\n{exc}" if exc.output else str(exc)
```

这正是 pi-mono `agent-loop.ts` 的 `executePreparedToolCall` 在做的事(`agent-loop.ts:666-707`):把每次 `tool.execute()` 抛出的错误折成一条普通的 `isError` tool result,而不是让异常终止整个 turn。也就是说工具层认为失败就是失败,循环层保证失败总能变成一条模型看得到的 tool result,让模型下一步修正。

第二处差异是长输出的处理方向:保尾不保头,并把完整输出转存到临时文件。`tool/truncation.py` + `tool/output_accumulator.py`:

```python
def truncate_tail(output: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    data = output.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return output
    tail = data[-max_bytes:].decode("utf-8", errors="ignore")
    return f"[... output truncated to the last {max_bytes} bytes ...]\n{tail}"
```

```python
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix=f"{self._temp_file_prefix}-", delete=False
        ) as f:
            f.write(output)
            full_output_path = f.name

        return (
            f"[... output truncated to the last {MAX_OUTPUT_BYTES} bytes. "
            f"Full output: {full_output_path} ...]\n"
            f"{truncated.split('\\n', 1)[-1]}"
        )
```

因为 bash 输出最有用的信息(报错、最终结果)常在最后几行,pi-mono 的 `OutputAccumulator` + `truncate.ts` 用 2000 行/50KB 的预算做同样的事;这里简化成单一字节上限,但保留了"截尾 + 全量落盘"这个双重策略,而不是像 kimi-cli/opencode 那样只做一次性硬截断。

第三处差异是根本没有 `MAX_STEPS`。`run.py` 的 `turn()` 是纯 `while True`,唯一的停止条件是"这轮响应没有 tool calls":

```python
        while True:
            message = chat(messages).choices[0].message
            messages.append(message.model_dump(exclude_none=True))
            ...
            tool_calls = message.tool_calls or []
            if not tool_calls:
                return  # model chose not to call a tool -- turn is done
```

对应 pi-mono `agent-loop.ts:170-260` 的 `runLoop`:`hasMoreToolCalls` 只在上一条 assistant message 真的带 tool calls 时才保持 true,循环在模型第一次不调用工具时立即退出。pi-mono 不加人为步数上限,信任模型自己停,真正的安全阀是人在中途 Ctrl-C(这个 TUI demo 同样支持 Ctrl-C 退出)——这里如实保留了这个设计,没有像其他变体那样补一个硬 `MAX_STEPS`。

这条路线预计能补上 Step 0 的一部分失败:模型可以跑测试、看 traceback、验证 patch 是否能应用,而不是只凭语言模型记忆直接写答案。失败折回 tool result 这一点尤其关键,因为真实调试里失败输出通常比成功输出更有信息量。它的短板是无状态 subprocess 和无硬上限:模型如果忘了路径不持久会多走一两轮;如果陷入重复试错,代码不会自动截断循环——这是"信任模型自己停"这个生产取舍本身带来的代价,不是实现疏漏。

## 怎么跑

```bash
uv run python -m agent_ladder.steps.step_1_bash.pi_mono.run
```

打开终端聊天界面后可以直接让模型跑命令,例如"帮我看看当前目录下有几个 Python 文件"。能看到 `ToolCallEvent` 和 `ToolResultEvent` 交替出现,直到模型自己决定不再调用工具、给出最终文字回复。
