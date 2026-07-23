# Step 1 —— 万能 bash 工具 + 工具调用循环

## 这一步是什么

最简单地说,Agent = LLM + tool:LLM 像大脑,负责理解问题、规划下一步;tool 像手,负责真正作用于外部世界。Step 0 已经是一个能连续聊天的循环,但每轮只能让 LLM 直接回文本,没有任何工具可用;Step 1 给这个循环加上第一条"手":一个万能 `bash` 工具。

先看一个最小例子:用户问"当前目录下有什么文件?"模型不会自己去读磁盘,它只会回一个结构化请求:"我要调用 `bash`,参数是 `ls`"。真正执行 `ls` 的是外层 harness;harness 拿到输出后,再把这段输出作为一条 tool result 塞回对话历史。模型下一轮看到 `ls` 的结果,才继续回答用户。

把这件事拆开看,实际发生的是下面这几步。字段有省略,但方向和 Step 1 代码一致。

第一步,人发送一条普通 user message:

```python
messages = [{"role": "user", "content": "当前目录下有什么文件?"}]
```

第二步,harness 调 LLM。它不只传 messages,还会把可用工具的说明一起传过去:

```python
response = complete(
    messages=messages,
    tools=[{
        "type": "function",
        "function": {
            "name": "bash",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    }],
)
```

第三步,大模型返回 assistant message。这里它没有直接回答用户,而是说:"我要调用 `bash`,参数是 `ls`":

```python
{
    "role": "assistant",
    "content": None,
    "tool_calls": [{
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "bash",
            "arguments": "{\"command\": \"ls\"}",
        },
    }],
}
```

第四步,harness 读取大模型返回的 tool call,按函数名找到本地函数,把参数解析出来执行:

```python
message = response.choices[0].message
messages.append(message.model_dump())

for call in message.tool_calls or []:
    tool_name = call.function.name
    args = json.loads(call.function.arguments or "{}")

    if tool_name == "bash":
        output = run_bash(**args)
    else:
        raise ValueError(f"unknown tool: {tool_name}")

    messages.append({
        "role": "tool",
        "tool_call_id": call.id,
        "content": output,
    })
```

第五步,harness 再把带有 tool result 的 messages 发给 LLM。此时模型看到的不再只是用户问题,还包括 `ls` 的真实输出;如果它认为信息够了,这一轮就直接返回最终文本答案,不再返回 tool call:

```python
response = complete(messages=messages, tools=[BASH_TOOL])
message = response.choices[0].message

if not message.tool_calls:
    messages.append(message.model_dump())
    return message.content
```

宏观上,这就是 tool calling loop:LLM 负责决定"要不要用工具、用哪个工具、参数是什么";harness 负责按函数名找到本地实现、执行它、把结果喂回模型。单轮 user 消息内部,这个过程可以重复很多次,直到某一轮模型不再请求工具,而是直接给出最终答案。

## 结果

尚未在固定 SWE-bench 子集上跑出可比的一行分数;当前只保留 step 本身的教学实现和本地单元测试。

## 结果分析

这一步理论上能补上 Step 0 最明显的短板:模型不再只能凭空写答案,而是可以观察仓库、读取文件、运行命令和测试,再根据工具结果继续行动。成功样本预计会集中在"能靠若干 shell 命令定位并验证"的问题:比如看错误栈、搜索符号、跑目标测试、检查 patch 能否应用。

主要失败会来自万能 bash 工具本身的边界:工具面太宽,模型容易把读文件、搜索、编辑、测试都塞进脆弱的 shell 字符串;每次调用是新 shell,如果模型误以为 `cd` 或环境变量会跨调用保留,就会多走弯路;长输出也只是粗暴截断,还没有上下文管理能力。后续章节拆出专用 read/search/edit 工具,就是为了解决这些失败模式。

参考 agent 设计对比如下。`minicode/run.py` 是综合版教学实现:只保留一个 `bash` 工具、一个 `step(messages)` 和一个 `turn(messages)` 循环。每次工具调用都启动新的 `bash -c` 子进程,stdout/stderr 合并成一段文本,非零退出码追加到输出末尾;停止条件统一为"这一轮 assistant message 没有 tool calls"。

`kimi/` 和 `qwen_code/` 是最接近这个综合版的两条来源。它们都把实现拆成三层:一次 LLM 调用、执行这一轮返回的 tool calls、外层 while 循环。工具面也保持很小,基本就是一个 shell command;没有专用 read/edit/search,也不靠模型输出 `DONE` 这种魔法字符串结束,而是看到没有 tool calls 就停。

`opencode/` 的重点是手写外层 loop。真实 opencode 没有直接依赖 SDK 的自动多步 agent loop,而是在每一轮模型调用之间插入自己的权限、持久化、压缩等工程逻辑。这个版本保留它的核心形状:一轮模型调用之后看有没有 tool calls,有就执行并继续,没有就结束;为了教学可控,这里用硬 `MAX_STEPS` 代替 opencode 更软的 max-step 提醒机制。

`codex/` 展示的是 Codex 式 turn loop:模型返回 tool calls 就需要 follow-up,执行工具并把结果写回历史;没有 tool calls 就说明模型已经给出最终答复。真实 Codex 可以并发调度多个工具调用,这里按顺序执行,因为 Step 1 只有一个 shell 工具,并发 bash 对教学收益不大。

`pi_mono/` 也是 fresh subprocess 设计,但更强调错误和长输出怎么进上下文:非零退出或超时被当成工具失败,再由 loop 包成普通 tool result 交给模型;长输出截尾,同时把完整输出落到临时文件,让模型需要时再读。这个版本也刻意不加硬 `MAX_STEPS`,贴近 pi-mono 信任模型自己停下来的设计。

`claude_code/` 介于"每次全新 shell"和"持久 shell session"之间。它每次仍然启动新子进程,所以环境变量、alias、shell function 不跨调用保留;但会追踪上一轮命令结束后的 cwd,下一轮从这个 cwd 开始,所以 `cd` 看起来是持久的。它也把工具失败作为结果喂回模型,而不是让 Python 异常中断整个 loop。

`hermes_agent/` 使用 `terminal` 这个名字,强调 cwd 和 exported env 跨调用持久。但它不是靠长驻 shell 进程实现,而是每次新开 bash,执行前 source 上一轮导出的环境快照,执行后记录新的 cwd/env。这个版本保留这种"用文件快照伪造持久状态"的设计,砍掉了真实实现里的 PTY、远程 sandbox、权限和后台任务。

`trae_agent/` 是另一端:真正长驻一个 `/bin/bash` 进程,cwd、环境变量和 shell 历史都自然跨调用保留。它用 sentinel 判断一条命令什么时候结束;如果命令卡死,整个 session 会被杀掉,模型需要显式 `restart` 才能恢复。这个版本说明了持久 shell 的好处和代价:状态自然保留,但一个坏命令也可能把整只"手"卡住。
