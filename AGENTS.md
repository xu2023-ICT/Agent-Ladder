# Agent Instructions

## Code Comments

Keep code comments and docstrings focused on the code's purpose, behavior, and non-obvious design constraints.

Do not put local environment details, private gateway URLs, one-off debugging findings, or machine-specific setup notes in code comments. Keep private planning notes and one-off run artifacts out of the public repo.

## Step 目录结构:代码放哪、SWE-bench 代码在哪跑

每一步的代码分两处放,职责不重叠:

- **`src/agent_ladder/steps/step_N_xxx/`** —— 这一步教学的核心代码,不依赖 SWE-bench,读者不装 Docker 也能跑起来。放:
  - 这一步新增能力本身的实现(例如 step 0 的 `chat(messages)`)。对话历史怎么维护是这一步自己的事,永远别把它藏进 `shared/`——不同 step 维护状态的方式不一样(step 0 只是累积 messages,后面几步要塞进工具调用结果),抽成共享 helper 会把"这一步在教什么"也一起藏起来。
  - `turn(messages)`:维护这一步自己对话状态(至少是累积的 messages 列表,原地追加)的闭包/生成器,把每轮结果适配成 `shared/tui.py` 的事件流(`TextEvent`/`ToolCallEvent`/`ToolResultEvent`)。**忘记累积历史是最容易犯的错**——如果每轮 `turn()` 都重新起一条只有当前输入的对话,TUI 里连续打字会像是在跟一个失忆的模型说话,不是真的在聊天。
  - `if __name__ == "__main__": AgentChatApp(turn(...)).run()` —— 这样 `uv run python -m agent_ladder.steps.step_N_xxx.run` 直接打开一个能打字聊天的终端 demo。`textual`(`AgentChatApp` 依赖)是默认依赖(每一步都要用它跑 demo,没必要单独分组),`shared.tui` 的 import 可以放模块顶部,不用懒加载。
  - **不放**:跑 SWE-bench 子集、抽 patch、写 predictions.jsonl、调评测 harness 这类东西。
- **`src/agent_ladder/benchmarks/swebench/`** —— SWE-bench 代码统一放这,不进 `steps/`:
  - **`step_N/run.py`**:每个 step 一个子文件夹,和 `steps/` 下的教学目录一一对应,负责在固定 30 条子集上跑这一步(import `steps/step_N_xxx/run.py` 里的核心函数)、抽 patch、写这个子文件夹自己的 `predictions.jsonl`。
  - **`evaluate.py`**:打分入口,所有 step 共用,不按 step 拆分(`uv run python -m agent_ladder.benchmarks.swebench.evaluate <predictions_path> <run_id>`)。
  - **`dataset.py`/`repo.py`/`swebench_lite_30.json`**:跨 step 共用的子集加载、仓库 checkout 缓存。
  - **`oracle.py`**:Oracle 单轮 prompt 构造,目前只有 step 0 用。

判断一段代码该放哪边:读者想看懂"这一步在教什么"必须读到它 → 放 `steps/`;只是为了在 SWE-bench 上产出一个可比分数 → 放 `benchmarks/swebench/`。

## Step README 写法

每个 `steps/step_N_xxx/README.md` 是写给"想快速看懂这一步在教什么"的读者看的,不是运行手册或排错笔记。固定四段,不多不少:

1. **这一步是什么**:一两句话说清这一步新增的核心能力本身,不是测试机制。例如"没有工具调用循环、没有工具,一次 completion 就是整个 step"。
2. **怎么跑**:怎么跑**这一步自己的代码**——一段最小可用的调用示例(通常几行 Python,把这一步的核心函数/入口跑起来),让读者看到这一步教的东西长什么样。不是怎么跑 SWE-bench;benchmark 的生成/打分命令不属于这一段。
3. **结果**:在固定 benchmark 子集上的一行分数,可以带一句跟历史基线或上一步的对比。不放怎么跑分的命令——benchmark 只是用来产出一个可比的数字,不是教学内容。
4. **结果分析**:必须放在每章 README 的最后。结合这一步的架构设计解释这个数字为什么是这样、成功样本有什么共同点、失败样本主要卡在哪几类、这些失败给下一章新增能力埋了什么伏笔。具体失败的 instance id、失败模式这类能支撑分析的细节留在这里,但只保留能解释"为什么"的部分,别堆砌运行日志式的流水账。

## 多参考 Agent 对比章节的目录结构

当一章要教的能力值得跟主流 code agent 的真实设计对比时(目前每一章都是,参见 `step_1_bash`),`steps/step_N_xxx/` 下面按下面的骨架组织,不是一个 `run.py` 打天下:

- **`minicode/`** —— 作者自己理解的最简实现,不对应任何具体真实项目,是这一章"从第一性原理出发该怎么设计"的基线版本。
- **按参考 agent 命名的文件夹**(`claude_code/`、`codex/`、`hermes_agent/`、`kimi/`、`opencode/`、`pi_mono/`、`qwen_code/`、`trae_agent/` 这一组,后续章节沿用同一组名字),每个对应一个真实 code agent 项目在这一章能力上的设计。

每个文件夹(含 `minicode`)内部:

- `run.py` 必须能一键跑起来 TUI demo(`uv run python -m agent_ladder.steps.step_N_xxx.<folder>.run`),这是唯一跨文件夹强制一致的东西。
- 除此之外内部怎么拆文件、核心逻辑叫什么名字、要不要单独的 `tool/` 包,不强求跨文件夹一致——参考对应的真实项目(`reference-agents/<agent>` 本地 checkout)自己的架构来定。参考 agent 的实现要保留真实的架构和关键实现细节(哪个文件对应真实项目哪个源码文件,值得在 README 里点名),但要屏蔽掉大量防御性代码——sandbox、权限审批、PTY、后台任务队列、并发调度这类生产 hardening 不是教学重点,砍掉。
- 调研发现(读了参考项目哪些源码文件、复刻了什么设计、有意砍掉了什么)直接写进这个文件夹自己的 README.md,通常在"这一步是什么"和"结果分析"里点出具体源码文件路径。
- 对应一个独立测试文件,1:1 命名(如 `tests/test_step_N_xxx_minicode.py`、`tests/test_step_N_xxx_claude_code.py`),不同文件夹的测试不合并到一个文件里。

## GitHub Push

For this repository, do not use GitHub SSH on port 22. The local network closes that connection.

Use GitHub SSH over port 443 with the dedicated GitHub key:

```bash
git config url.ssh://git@ssh.github.com:443/.insteadOf git@github.com:
git config core.sshCommand 'ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'
git branch --set-upstream-to=origin/main main
```

After the config is present, normal commands should work:

```bash
git push
git pull
git fetch
```

If a one-off push command is needed, use:

```bash
GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519_github -p 443 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' \
  git push -u ssh://git@ssh.github.com/xu2023-ICT/Agent-Ladder.git main
```
