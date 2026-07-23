# Qwen Code

这个变体和 `minicode` 共用同一个骨架——一个万能 shell 工具 + `chat`/`step`/`turn` 循环——但工具本身按 qwen-code 真实的 `ShellTool`(`packages/core/src/tools/shell.ts`)重新量了一遍参数和输出细节,能看出同一个"bash 工具"在不同项目里被拧了哪些旋钮。

第一处不同是名字和参数默认值。工具不叫 `bash` 而叫 `run_shell_command`,`timeout` 的默认值和上限也不是 minicode 那种"默认 60 秒、没有上限",而是对应真实 `ShellTool` 的 `DEFAULT_FOREGROUND_TIMEOUT_MS = 120000` 和硬上限 `600000`:

```python
DEFAULT_TIMEOUT_SECONDS = 120
MAX_TIMEOUT_SECONDS = 600
```

真实 qwen-code 在参数校验阶段就拒绝超过上限的 `timeout`,这里为了省掉一整套校验层,选择在执行前直接夹紧:

```python
def run(command: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    timeout = min(timeout or DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS)
    return ShellToolInvocation({"command": command, "timeout": timeout}).execute()
```

真实工具的参数面比这大——还有 `is_background`(后台任务)和 `directory`(用绝对路径代替模型手写 `cd`,这是 qwen-code 相对 kimi-cli 多给的一个可选参数)。这两个都没有实现:后台任务需要一整套任务注册表和通知机制,不是这一章的重点;`directory` 则是刻意跟 kimi-cli 保持一致——两个真实项目在"要不要给 cwd 参数"这个问题上给出了不同答案,这里选边站 kimi-cli 一侧,把这个设计选择留给读者自己比较。

执行模型和 minicode 一样,还是一次性、非交互式的 `bash -c` 子进程,stdin 关闭、stdout/stderr 合并;区别只在输出收尾的写法——不管成功还是失败都固定追加 `[exit code: N]`,而不是 minicode 那种只在非零退出码时才追加：

```python
completed = subprocess.run(
    ["bash", "-c", command],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    timeout=timeout,
    text=True,
)
...
return f"{truncate_tool_output(completed.stdout or '')}\n[exit code: {completed.returncode}]"
```

截断阈值也从 minicode 的 `MAX_OUTPUT_CHARS = 20_000` 换成了 `30_000`——这个数字直接抄自真实 `shell.ts` 里 shell 工具自己的 `maxOutputChars`。但真实 qwen-code 在这里明显更重:它把完整输出存到临时文件,只给模型看头尾预览加一个文件指针(`utils/truncation.ts` 的 `truncateAndSaveToFile`),这里只搬了"限制单次输出大小"这一个目的,没有搬临时文件生命周期管理那层复杂度:

```python
MAX_OUTPUT_CHARS = 30_000

def truncate_tool_output(output: str) -> str:
    if len(output) <= MAX_OUTPUT_CHARS:
        return output
    hidden = len(output) - MAX_OUTPUT_CHARS
    return f"{output[:MAX_OUTPUT_CHARS]}\n...[truncated, {hidden} more chars]"
```

工具描述文案也刻意反着写。真实 qwen-code 现在的 prompt 会告诉模型不要用 shell 做 cat/grep/find/sed,改用专用工具;但 Step 1 还没有专用工具,所以这里的 `DESCRIPTION` 明确要求模型把它当瑞士军刀用,连"不要用于类似构建/测试的命令"这种暗示都反过来写清楚:

```python
DESCRIPTION = (
    "Execute a shell command and return its output. This is the only tool "
    "available, so use it for everything a terminal can do -- listing and "
    "reading files (ls/cat), searching (grep), editing (sed), running "
    "tests, git, etc. -- not just for things that look like build/test "
    "commands. ..."
)
```

qwen-code 真实的 `ToolResult` 类型还把"喂给模型的内容"(`llmContent`)和"展示给用户的内容"(`returnDisplay`)拆成两个字段,为后面章节(比如 edit 工具给用户看 diff、给模型看一句简短确认)预留接口;这个变体的 bash 工具还没必要分裂成两个字段,一段文本同时喂模型和展示给用户就够了。`tool/registry.py` 里一个极简 `ToolRegistry`(名字到 `(schema, run)` 的映射)也是照着真实 qwen-code 的 registry 抽象搭的骨架,这一步只有一个工具,还看不出它的价值,留给后面工具变多时再体会。

## 怎么跑

```bash
uv run python -m agent_ladder.steps.step_1_bash.qwen_code.run
```

也可以不开 TUI,直接在代码里跑:

```python
from agent_ladder.steps.step_1_bash.qwen_code.run import turn

messages = []
for event in turn(messages)("这个仓库用的什么 Python 版本?"):
    print(event)
```

工具调用和执行结果会在 TUI 里分别渲染出来,可以直接看到模型每一步在调什么命令、拿到了什么输出。
