# Step 0 —— 裸聊天

没有 agent loop(模型自己决定下一步做什么),没有工具——就是跟大模型一句一句聊:每轮把完整对话历史发过去,换回一条回复,一次 `litellm.completion()` 就是整个 step。

拿 SWE-bench 打分时用的是这句话的极限版本:**Oracle 模式**,把标准答案改动过的文件内容 + issue 原文直接喂给模型,一次性要它写出 diff。Prompt 怎么拼的细节、跑子集/写 predictions/打分这些都是 SWE-bench 专用的基础设施,不是这一步教学的重点,放在 `agent_ladder.benchmarks.swebench.step_0` 下,不在这个目录里。

## 怎么跑

```bash
uv run python -m agent_ladder.steps.step_0_bare_chat.run
```

打开一个终端聊天界面,可以连续输入。注意它没有 agent loop、没有工具,`turn()` 只是把每轮对话摞进 messages 列表原样发给模型——模型记得你说过什么,但不会替你做任何探索或编辑。

核心教学代码在 `chat.py`;`run.py` 只负责启动这个 TUI demo。

## 结果

`qwen3-max`,SWE-bench Oracle 模式,固定 30 条子集:**7/30 resolved ≈ 23.3%**(对照论文历史基线 Claude 2 oracle 模式 4.8%)。

## 结果分析

- Oracle 模式是"作弊"的:该改哪个文件是喂进去的,不用模型自己找。所以这条曲线的起点天然偏乐观,跟 step 1 起"agent 自主探索"测的不是同一种能力——曲线在 0→1 之间完全可能不升反降,这是预期内的,不是回归。
- 没通过的大头(19/30)不是"模型不会做",而是回复里思路对、但不是干净的 unified diff(hunk 行号算错、缺上下文行)。这正是 step 2 引入专用 `edit` 工具要解决的问题——裸聊天没有结构化输出的手段,只能靠模型自己把格式写对。
- 4 条(`django__django-11019`、`django__django-14608`、`mwaskom__seaborn-2848`、`sphinx-doc__sphinx-8273`)patch 完全打不上,重跑结果一致,是同一类格式问题的极端情况。
