# OpenCode

这个目录按 [OpenCode](https://opencode.ai) 的实现路线展示 Step 1,骨架和 `minicode/` 一样:一个万能 `bash` 工具,`chat`/`step`/`turn` 三个函数,停在某轮响应不再带 tool calls。差异集中在 loop 的归属和长输出的处理策略上。

参数面几乎和 minicode 一样窄,只是默认超时不同。`tool/schema.py`:

```python
DEFAULT_TIMEOUT = 120
NAME = "bash"

SCHEMA = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Full shell command string to run, e.g. `ls -la` or `pytest tests/ -x`.",
                },
                "timeout": {
                    "type": "number",
                    "description": f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
                },
            },
            "required": ["command"],
        },
    },
}
```

opencode 仓库里同时存在两代实现——生产 CLI 的 `packages/opencode/src/tool/shell.ts` 和正在替换它的 V2 重写 `packages/core/src/tool/bash.ts`——两代独立演化却收敛到同一个 `command`(必填)+ `workdir`(可选,代替 `cd`)+ `timeout`(可选)参数集。连同 kimi-cli 一起,三份参考实现都同意"最小面就是 command+timeout",`workdir` 因此被判定为锦上添花而非必需,先不加,模型仍要在 command 里自己 `cd`,把"加 workdir 教模型别用 `cd &&` 反模式"留给后面章节。

执行本身和 minicode 同构(新起 `bash -c` 进程、stdin 关闭、stdout/stderr 合并),但返回格式有一处系统性差异:opencode 的成功输出也总是带 exit code,不像 kimi-cli 那样区分"成功就干净、失败才啰嗦"。`tool/executor.py`:

```python
def execute(command: str, timeout: float) -> str:
    try:
        completed = subprocess.run(
            ["bash", "-c", command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.output or ""
        return f"{truncate_output(output)}\n\nCommand timed out after {timeout}s."

    output = completed.stdout or "(no output)"
    return f"{truncate_output(output)}\n\nExit code: {completed.returncode}"
```

长输出这里用固定字符数硬截断(`tool/truncate.py` 的 `MAX_OUTPUT_CHARS = 20_000`):

```python
def output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    hidden = len(text) - MAX_OUTPUT_CHARS
    return f"{text[:MAX_OUTPUT_CHARS]}\n...[truncated, {hidden} more chars]"
```

真实 opencode 的策略更精细,是"保留尾部若干行 + 溢出部分完整写入临时文件,输出里附一行 `Full output saved to: <path>` 提示模型用 Read/Grep 去查",这里只搬了"防止上下文被打爆"这个目的,没有搬转存文件这层机制。真实 opencode 的 `shell.txt` prompt 里还有一大段"不要用 bash 做 X,改用专用工具 Y"(`find`→Glob、`grep`→Grep、`cat/head/tail`→Read、`sed/awk`→Edit)——这是它已经拆出专用工具之后才需要的话术,和 Step 1 的工具描述方向正好相反,所以这里的 `DESCRIPTION` 反过来明确鼓励模型把 `ls`/`cat`/`grep`/`sed` 都塞进这一个 bash 工具里用。

opencode 变体真正想展示的是"loop 是应用层资产,不是 SDK 内置行为"。真实 opencode 的 `session/prompt.ts` `runLoop()` 是一个手写 `while (true)`,故意不用 AI SDK 内置的多步 agent loop(不传 `stopWhen`/`maxSteps` 给 `streamText`),因为应用需要在每一步之间插入权限、存储、压缩和 UI 逻辑。`run.py` 的 `step`/`turn` 复刻这个两层形状:`step` 是一次模型调用 + 分发这轮全部 tool calls;`turn` 是外层 `while`,一直调用 `step` 直到某轮没有 tool calls 要分发——这个停止条件复用 provider 原生的 `tool_calls`/`finish_reason` 语义,对应真实实现里 `finish !== "tool-calls"` 的判断,不需要模型说 `DONE` 或调用额外的完成工具。

`session/prompt.ts` 的 `runLoop` 在这一点上留了一个值得记住的教训:它不完全信任 provider 返回的 `finish_reason`,因为部分 provider 在消息里明明还带着未执行的 tool_calls 时,`finish_reason` 却错误地报告成 `stop`,所以停止判断还要在消息里再查一遍有没有遗留的 tool call parts 作为兜底。这里的教学版没有复现这个兜底,因为本地跑的模型没有这个怪癖,但这提示"tool_calls 是否为空"这个停止条件在真实多 provider 环境下并不总是可以直接信任单一字段。

max-steps 上也有差异:opencode 默认其实是*无上限*(`agent.steps ?? Infinity`),配置了上限时是靠注入一句"请停止调用工具"的软提示来收尾(`packages/core/src/session/runner/max-steps.ts`),而不是硬中断。这里的 `MAX_STEPS` 是硬中断——更容易在教学场景下推理,也和其他变体的防护方式保持一致。

短板是工具语义完全无状态,模型要自己管理路径、转义和命令串联;如果后续要提升 SWE-bench 可靠性,下一步应该把最脆弱的读/搜/改从 bash 字符串里拆成专用工具。

## 怎么跑

```bash
uv run python -m agent_ladder.steps.step_1_bash.opencode.run
```

也可以直接调用工具:

```python
from agent_ladder.steps.step_1_bash.opencode.tool import run

print(run("echo out; echo err >&2"))
```

TUI 中可以让模型先读目录、再读文件、再运行测试;这些步骤都会通过同一个 `bash` 工具发生。
