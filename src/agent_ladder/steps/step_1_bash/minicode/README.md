# minicode

## 这一步是什么

只保留一个 `bash` 工具、一个 `step(messages)` 和一个 `turn(messages)` 循环,从第一性原理出发展示"LLM + tool + loop"这个最小骨架。

一个工具要让模型能用,首先得有一份定义。`tool/schema.py` 里的 `BASH_TOOL` 就是这份定义,每次请求都会带给模型:

```python
BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Run a bash command and return its output. This is the only tool "
            "available -- use it for everything: listing and reading files, "
            "searching, editing (e.g. with sed or a heredoc), running tests, "
            "checking git status, and so on. ... Each call runs in a brand "
            "new shell -- the working directory, environment variables, and "
            "shell history are NOT preserved between calls -- so chain "
            "related commands in one call with `&&`, `;`, or `|` instead of "
            "relying on state from a previous call."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"etype": "string", "dscription": "The bash command to execute."},
                "timeout": {"type": "integer", "description": "Timeout in seconds. Defaults to 60."},
            },
            "required": ["command"],
        },
    },
}
```

`function.name` 是工具的名字(`bash`,模型靠这个名字告诉 harness 它要调用哪个工具);`function.description` 是一段自然语言说明,告诉模型这工具能干什么、该怎么用(比如提醒模型每次调用都是全新 shell、状态不跨调用保留,得把相关命令用 `&&`/`;`/`|` 串起来);`function.parameters` 是 JSON Schema,声明这个工具接受什么参数——这里只有两个:`command`(`string`,`required`,模型必须给的 bash 命令本身)和 `timeout`(`integer`,可选,不填就用 `DEFAULT_TIMEOUT` 也就是 60 秒)。模型看到这份定义,才知道"有个叫 bash 的工具能用,调用时要传 command"。

光有定义还不够,模型自己不会真的帮你跑命令——它的回复终归只是一段消息。模型决定调用 `bash` 时,`step()` 里拿到的 `message.tool_calls` 长这样,`arguments` 是一段字符串化的 JSON,不是现成的 Python 值:

```python
message.tool_calls == [
    {
        "id": "call_abc123",
        "type": "function",
        "function": {"name": "bash", "arguments": '{"command": "ls -la"}'},
    }
]
```

harness 得自己把这段 JSON 解析出来,再按参数去调真正的执行函数——这就是 `run.py` 里 `step()` 在做的事:

```python
for call in message.tool_calls or []:
    args = json.loads(call.function.arguments or "{}")  # 字符串 -> {"command": "ls -la"}
    output = run_bash(**args)                            # 真正执行,拿到结果字符串
    messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
```

`run_bash`(`tool/shell.py`)拿到解析后的 `command`/`timeout`,起一个全新的、非交互式的 `bash -c command` 子进程去真正执行,把 stdout/stderr 合并、超长截断、非零退出码追加提示,拼成一段模型能读的文本:

```python
def run_bash(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    result = subprocess.run(
        ["bash", "-c", command],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        output += f"\n(exit code: {result.returncode})"
    return output or "(no output)"
```

这段返回值最终被塞进 `{"role": "tool", "tool_call_id": call.id, "content": output}`,追加回 `messages`,模型下一轮才能看到命令真正的执行结果。

`chat` 是带工具 schema 的一次 completion;`step` 执行这一轮 assistant message 里的所有 tool calls 并追加 `role: "tool"` 消息;`turn` 用 `MAX_STEPS` 防 runaway,一直调用 `step` 到模型不再请求工具——停止条件是"这一轮响应没有 tool calls",而不是靠模型输出 `DONE` 这种魔法字符串。

## 怎么跑

```bash
uv run python -m agent_ladder.steps.step_1_bash.minicode.run
```

## 结果

尚未为这个变体单独跑固定 SWE-bench 子集分数。当前本地测试覆盖了 stdout/stderr 合并、非零退出码、timeout、stdin 关闭、schema 和模块导入。

## 结果分析

这个版本的优点是最小、直接、容易读:没有任何一个参考 agent 的历史包袱,`run.py` 一个文件就能看完整个 loop。工具面窄到只有 `command`,每次调用都是独立子进程,不会被上一条命令留下的 cwd/env 污染,也不用担心交互式程序卡住整个 agent——stdin 直接关闭,读 stdin 的命令会很快 EOF。

代价同样来自这种无状态设计:模型必须自己记得每次显式 `cd` 或把依赖命令串进同一个 command,连续的多步操作(比如先 `cd` 进某个目录、再跑测试)很容易因为模型忘记这一点而失败;长输出只做粗暴截断,没有专门的上下文管理;编辑文件也全靠模型自己拼 shell 字符串(heredoc、`sed` 之类),脆弱且难以验证。这些短板正是后续章节拆出专用 read/edit/search 工具要解决的问题。
