# trae-agent

`minicode` 每次调用都起一个全新的 `bash -c` 子进程;这个变体反过来,工具背后是一个模块级、长驻的 `/bin/bash` 进程,cwd、环境变量和 shell 历史跨调用保留。这个选择来自 `reference-agents/trae-agent/trae_agent/tools/bash_tool.py`,也就是 Anthropic computer-use bash tool 参考实现的衍生版本。模型可以先 `cd src`,下一次再 `pwd` 或 `pytest` 时仍然处在同一个 shell 状态里:

```python
class _BashSession:
    def __init__(self):
        self._sentinel = f"___AGENT_LADDER_BASH_DONE_{uuid.uuid4().hex}___"
        self.process = subprocess.Popen(
            ["/bin/bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
```

长驻进程带来一个新问题:minicode 里子进程跑完 `subprocess.run` 就返回,天然知道命令结束了;这里的 `/bin/bash` 进程永远不退出,得自己判断"这一条命令的输出到哪里结束"。做法是 sentinel 协议——每个 session 生成一个随机 sentinel,把 `command` 写入 stdin 后紧跟一段 `printf` trailer,让 shell 打印 `sentinel + exit_code + sentinel`,Python 端从 stdout 原始字节流里一直读到匹配到完整 trailer 为止:

```python
trailer = f"\nprintf '\\n{self._sentinel}%s{self._sentinel}\\n' \"$?\"\n"
self.process.stdin.write(command.encode() + trailer.encode())
self.process.stdin.flush()
...
while not self._trailer_re.search(buf):
    chunk = os.read(self.process.stdout.fileno(), 4096)
    if not chunk:
        break
    buf += chunk
```

随机 sentinel 是为了避免模型命令本身的输出恰好撞上固定 marker 而污染解析。这里对真实源码做了一个关键修正:`bash_tool.py` 原版会把命令包在 `(...)` 子 shell 里再追加 sentinel,方便 `$?` 稳定反映命令自身的退出状态;但这样 `cd`、`export`、变量赋值都只影响子 shell,回写不到长驻父 shell,直接违背工具描述里"state is persistent"的承诺。这里去掉了外层括号,让命令直接在长驻 session 里执行,因为这个变体要教的重点正是持久 shell 的真实状态保留。

参数面上比 minicode 多一个 `restart`。minicode 的 `timeout` 是模型可传的可选参数;这里 `command` 之外新增的是控制 session 生死的开关,而 `COMMAND_TIMEOUT = 120` 秒是固定值,不对模型暴露:

```python
@cached_property
def parameters(self) -> list[ToolParameter]:
    return [
        ToolParameter("command", "string", "The bash command to run.", required=True),
        ToolParameter("restart", "boolean", "Set to true to restart the bash session.", required=False),
    ]
```

真实 `bash_tool.py` 里 `restart` 是否放进 `required` 列表还要看 `model_provider`——OpenAI 的 strict-mode function calling 要求所有参数都出现在 `required` 里、可选参数改用 nullable 类型表达,这是纯粹的多 provider 兼容性细节;这里只对接一个 provider,`restart` 直接标成非必填。

这也是持久 session 相对一次性子进程最大的代价:minicode 里一条命令超时,杀掉的只是这一次子进程,下一次调用照样干净;这里超时或命令卡死会杀掉整条 session,而且不会自动恢复,模型必须显式传 `restart: true` 才能重建:

```python
def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
    if arguments.get("restart"):
        if self._session is not None:
            self._session.close()
        self._session = _BashSession()
    ...
```

stdout/stderr 的合并方式(`stderr=STDOUT`)和 minicode 一样是单流,这是相对真实 trae-agent 的一处简化——原版跑在 asyncio 上,能各自轮询两个独立 pipe,这里为了保持同步实现简单没有搬这层。

结构上按 trae-agent 的最小形状拆开:`tool/base.py` 放 `ToolCall`、`ToolResult`、`ToolParameter` 和 `ToolExecutor`;`tool/bash_tool.py` 放持久 `_BashSession`、`BashTool` 和 schema。真实项目还有 `docker_tool_executor.py` 负责把部分工具路由进容器,这个教学版没有 Docker 后端,只保留本地 executor。真实项目里 bash 也只是多个工具之一——编辑由 `str_replace_based_edit_tool` 负责,完成由 `task_done` 负责,而且 `bash` 和 `str_replace_based_edit_tool` 在 `AnthropicClient.chat()` 里会被翻译成 Anthropic 官方原生工具类型(`tool_bash_20250124`/`text_editor_20250429`),不是普通自定义 JSON schema 工具——这两个工具是 Anthropic 官方"配对"设计出来的一套组合(bash 管执行/观察,text editor 管可靠改文件),trae-agent 只是直接复用。本章故意不拆 edit/read/search,因为"只有 bash 时 agent 能走多远"正是这一步要观察的边界。

循环停止条件和 minicode 一样,用"这一步的回复有没有 tool_calls"判断模型是否给出最终回复,而不是真实 trae-agent 用的两种收尾方式——基类默认靠脆弱的文本子串匹配(`BaseAgent.llm_indicates_task_completed`),生产路径实际靠专门的 `task_done` 工具。tool-calling API 本身已经能告诉你模型是否还在调用工具,这是更贴近通用协议的信号。

## 怎么跑

```bash
uv run python -m agent_ladder.steps.step_1_bash.trae_agent.run
```

也可以直接调用工具验证持久状态:

```python
from agent_ladder.steps.step_1_bash.trae_agent.tool import BashTool, ToolCall, ToolExecutor

executor = ToolExecutor([BashTool()])
try:
    for command in [":", "pwd", "cd src", "pwd"]:
        result = executor.execute_tool_call(
            ToolCall(name="bash", call_id="manual", arguments={"command": command})
        )
        print(result.result)
finally:
    executor.close_tools()
```

在 TUI 路径里,`turn(messages)` 会把 user 消息、assistant 消息和每条 `role: "tool"` 结果都追加到同一个 `messages` 列表。和真实 trae-agent 把完整 history 下沉到 LLM client 内部不同,这里把累积历史留在 loop 代码表面,让"工具结果为什么能影响下一次模型调用"这件事在教学代码里可见。
