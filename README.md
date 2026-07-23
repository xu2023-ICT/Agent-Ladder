# Agent-Ladder

Agent-Ladder 是一个从 0 开始的小白项目。

它帮助你从最简单的纯聊天开始, 一步一步了解各家主流厂商和开源项目是怎么设计 code agent 的: 为什么要有 agent loop, 为什么要给模型工具, 为什么要拆出专用 edit/read/search, 为什么还需要上下文管理、sub-agent、权限审批和 sandbox。

每一章只新增一个主要能力, 并用同一套 benchmark 数据观察它带来的变化。你不只是在看代码怎么写, 也能直观看到每一项工具、每一次架构升级到底让 agent 多做了什么、少踩了什么坑。

每一章还会对照几个当前最流行的 code agent 的实现或公开设计, 包括 Claude Code、Codex CLI、OpenCode、Pi、Kimi CLI、trae-agent、Qwen Code 等。这个项目不是闭门造一个玩具 agent, 而是用一条从 0 到 1 的主线, 把主流 code agent 的设计拆开看。

## 第一章: 裸聊天

第一章没有工具调用循环, 没有工具, 没有文件读写, 也没有测试执行。它只保留大模型最原始的使用方式: 把完整对话历史发给模型, 拿回一条回复。

这一章要说明的是 code agent 的起点有多薄:

- 一次 `completion` 就是一轮回复。
- 连续聊天只是因为我们把历史 messages 保存下来, 下一轮再一起发过去。
- 模型不会主动探索仓库, 因为它没有任何工具。
- 模型不会修改文件, 因为它只能输出文本。
- 模型可以尝试写 patch, 但 patch 格式是否能干净应用完全依赖它自己。

对应代码在:

```text
src/agent_ladder/steps/step_0_bare_chat/
```

## 目录结构

```text
src/agent_ladder/
  steps/
    step_0_bare_chat/        # 第一章: 裸聊天
  benchmarks/
    swebench/                # 评测相关基础设施
  shared/                    # 跨 step 复用但非教学重点的基础设施
  scripts/                   # 维护脚本
tests/
```

读者必须看懂的 agent 机制放在 `steps/`; 为了跑分、缓存仓库、抽 patch、调用评测 harness 的代码放在 `benchmarks/swebench/`。
