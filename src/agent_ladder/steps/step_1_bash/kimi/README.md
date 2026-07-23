# Kimi CLI

这个目录按 [Kimi CLI](https://github.com/MoonshotAI/kimi-cli) 的实现路线展示 Step 1,和 `minicode/` 的最小骨架同构(`chat`/`step`/`turn`,一个 bash 工具,靠"这轮没有 tool calls"停止),差异全在工具本身和它对失败的处理方式上。

第一处差异是名字和参数面。真实 kimi-cli 的工具不叫 `bash` 而叫 `Shell`,`timeout` 有一个硬上限。`tool/schema.py`:

```python
DEFAULT_TIMEOUT = 60
MAX_FOREGROUND_TIMEOUT = 5 * 60

NAME = "Shell"

SCHEMA = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute."},
                "timeout": {
                    "type": "integer",
                    "description": (
                        f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}, "
                        f"capped at {MAX_FOREGROUND_TIMEOUT}."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}
```

真实 kimi-cli 还有 `run_in_background` + 必填的 `description`(用 `model_validator` 强校验),超过前台上限就要求模型改用后台任务,整套依赖独立的通知机制和 `TaskOutput` 轮询——这里没有实现,超时的命令直接被 kill。`tool/shell.py` 的 `run()` 用 `min()` 复刻这个 clamp:

```python
def run(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    timeout = min(timeout or DEFAULT_TIMEOUT, MAX_FOREGROUND_TIMEOUT)
    ...
```

同样没有 `cwd`/`workdir`,模型必须在 command 字符串里自己 `cd` 或用 `&&` 串联依赖命令——这一点和 minicode 一致。

第二处差异是成功/失败的输出不对称。minicode 无论成败都是同一段拼接逻辑;kimi-cli 的 `ToolResultBuilder.ok()`/`.error()` 分开处理,`tool/result.py` 里的 `ToolResultBuilder` 是它的简化版:

```python
class ToolResultBuilder:
    def __init__(self):
        self._chunks: list[str] = []

    def write(self, text: str) -> None:
        self._chunks.append(text)

    def output(self) -> str:
        text = "".join(self._chunks)
        if len(text) <= MAX_OUTPUT_CHARS:
            return text
        hidden = len(text) - MAX_OUTPUT_CHARS
        return f"{text[:MAX_OUTPUT_CHARS]}\n[...truncated, {hidden} more chars]"
```

`shell.py` 的 `run()` 用它来区分两条路径:成功只返回原始输出,失败额外追加 exit code,并调用 `_tail()` 找出最后几行非空输出附在后面,模型不用翻一屏 build log 去找真正的报错:

```python
    if completed.returncode == 0:
        return output or "(no output)"

    brief = _tail(output)
    result = f"{output}\n(exit code: {completed.returncode})"
    if brief:
        result += f"\n(tail: {brief})"
    return result
```

真实 `ToolResultBuilder` 还有 50000 字符总量、单行 2000 字符的精细裁剪预算,这里只用一个 20000 字符的粗截断代替。

第三处差异是循环的分层。minicode 的 `chat`/`step`/`turn` 是两层;kimi-cli 实际是三层:`kosong._generate.generate()`(单次 LLM 调用,只产出一条可能带 tool_calls 的 assistant message)、`kosong.step()`(给每个 tool_call 分发执行,`SimpleToolset.handle` 用 `asyncio.create_task` 支持并发)、`KimiSoul._agent_loop`/`_step`(`src/kimi_cli/soul/kimisoul.py`,真正"一直循环直到模型自己收工"的外层,判断 `StepOutcome.stop_reason` 是不是 `"no_tool_calls"`)。这里的 `step` 把前两层压成一次模型调用 + 执行这轮全部 tool calls;`turn` 是 `_agent_loop` 的 `while True`,把 approval、plan mode、compaction、后台任务、D-Mail 这些工程加固全部砍掉,只留 `MAX_STEPS` 这一道防 runaway 的安全阀,对应真实实现里的 `max_steps_per_turn`。

这条路线的优点是每个工具调用都是一次独立 subprocess,不会被上一次命令留下的 cwd/env/交互程序污染,模型跑了会读 stdin 的命令也会因为 stdin 关闭而很快 EOF,不会一直卡住。短板同样来自这种无状态模型:模型必须记住每次都显式 `cd` 或把依赖命令串进同一个 command;长输出只做粗截断;编辑文件仍然靠模型自己拼 shell 字符串。它能显著强于 Step 0 的裸聊天,但失败仍会集中在路径状态误判、shell 转义和脆弱编辑上。

## 怎么跑

```bash
uv run python -m agent_ladder.steps.step_1_bash.kimi.run
```

也可以不开 TUI,直接在代码里跑:

```python
from agent_ladder.steps.step_1_bash.kimi.run import turn

messages = []
for event in turn(messages)("这个仓库用的什么 Python 版本?"):
    print(event)
```

工具调用和执行结果会在 TUI 里分别渲染成 `ToolCallEvent`/`ToolResultEvent`,可以直接看到模型每一步调用了什么命令、拿到了什么输出。
