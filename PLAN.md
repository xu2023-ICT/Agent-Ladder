# Code Agent 教学版 — 项目计划

> 通过访谈（`/grill-me`）在 2026-07-20 达成的共识记录。后续实现应以此为准；若有变更，先更新本文档再动手。

## 1. 项目定位

- **形态**：公开教程 repo（GitHub），nanoGPT 式渐进结构——从最简单的纯聊天，一步一步加能力，最终扩展为完整 code agent。
- **不是**：自用脚本堆、也不是以文章为主要产出的系列（代码是主产出，文档随代码走）。
- **核心叙事**：每一步都跑同一把尺子（SWE-bench 子集），画出一条从 0 涨到可用的分数曲线；每一步都横向对比几家知名开源/泄露 code agent 在同一问题上的设计选择。

## 2. 技术栈

- **语言**：Python。
- **模型接入**：[LiteLLM](https://github.com/BerriAI/litellm)（**库**形式 `litellm.completion()`，不是 proxy sidecar），切换模型只改 model 字符串。
- **不使用任何 agent 框架**（LangGraph / OpenAI Agents SDK 等一律排除）——框架会把要教的 loop、工具调度、上下文管理全部藏起来，教学价值归零。

## 3. 横向对比对象

| 分类 | 项目 | 说明 |
|---|---|---|
| 主线 | Claude Code | 无开源，用泄露 system prompt / 工具定义，**仅架构对比，不实跑** |
| 主线 | Codex CLI | OpenAI 开源（Rust），**仅架构对比，不实跑** |
| 主线 | Kimi CLI | 锁定 **Python 原版**（`MoonshotAI/kimi-cli`，非后来的 TS 版 `kimi-code`），**仅架构对比，不实跑** |
| 主线 | SWE-agent / mini-swe-agent | Princeton，model-agnostic，**仅架构对比，不实跑** |
| 主线 | trae-agent | 字节开源（MIT，Python），SWE-bench Verified 曾登顶 75.2%，**仅架构对比，不实跑** |
| 主线 | Qwen Code | 阿里开源（Apache 2.0），**注意：是 Gemini CLI 的 fork**，**仅架构对比，不实跑** |
| 支线 | hermes-agent | Nous Research，自我改进/持久记忆型 agent，**只在系列后期"记忆/skills"章节登场**，仅架构对比 |
| 排除 | 智谱 (Zhipu) | 只开源模型（GLM），无自己的开源 code agent CLI |
| 排除 | 腾讯 CodeBuddy | CLI 存在但核心闭源，只有 npm 包 |
| 排除 | Cline | 早期讨论中为收敛主线数量而排除（Codex 的 approval modes 可部分覆盖其 approval 流对比价值） |

> **范围简化（2026-07-20 追加）**：原计划六家里除 Claude Code/Codex 外都要实跑，现改为**全部仅做架构对比，不实跑**——所有实跑资源集中到自研 9 步系列（单一模型 `qwen3-max`），六家只读源码、讲设计选择，不跑分。

读源码的方式：派多个 agent 并行去读，只看结论，不手动逐行读。

## 4. Benchmark 设计

- **固定子集，从 step 0 就用**：**30 条**，从 SWE-bench Lite 按 **12 个仓库**（实测修正：不是最初写的 11 个）分层抽样、**固定 seed=42**，`src/agent_ladder/scripts/select_subset.py` 生成，结果写死在 `src/agent_ladder/benchmarks/swebench/swebench_lite_30.json`，保证可复现、**从 step 0 到 step 8 全部跨步骤可比**。
  - 理由：条数太少（<10）分数抖动大，不可信；太多（50+）迭代变慢；30 条是常见的"看得出趋势又能反复跑"的折中点。
  - 范围澄清（相对早期草稿的变更）：原措辞是"从第一个具备 edit + bash 能力的 step 起"才用这个子集，暗示 step 0 单独处理。现在改为 step 0 也用同一个子集——否则曲线起点和后续步骤不在同一把尺子上，没法画成一条线。跟历史论文分数（如 Claude 2 在 Oracle 模式下 4.8%）的对照仅供参考，不是我们复现的对象（论文跑的是全量，量级不同）。
- **Step 0（纯聊天，无 loop 无工具）**：用 SWE-bench **Oracle 单轮模式**——把标准答案 patch 改动过的文件直接喂给模型，一次性要求生成 diff，无需 tool use。这是原始 SWE-bench 论文（2023, ICLR 2024）的基线方法。Prompt 模板照抄论文/官方 `swebench` 包的 "style-2" 格式（`src/agent_ladder/steps/step_0_bare_chat/oracle.py` 里手抄了一份，没有直接 `import swebench.inference...`，因为那条 import 链会拖进不需要的 `transformers` 依赖）。
- **全量 SWE-bench Lite（300 条）/ Verified（500 条）**：只在系列收尾章节，给自研系统（`qwen3-max`）跑一次，作为最终成绩单；六家参考 agent 不用它们跑分。
- **已知局限（需在教程中明确写出，不要回避）**：
  1. Step 0（Oracle 作弊式喂文件）和 step 1 起（agent 自主探索）测的不是同一种能力，曲线在 step 0→1 之间可能出现"不升反降"，这是预期内的、值得讲的一课，不是 bug。
  2. 六家横向对比全部是架构定性描述，没有任何一家有实测分数——不是只有 Claude Code / Codex 两家没跑，是刻意收敛范围，把实跑资源全部留给自研系列。
  3. 自研 9 步曲线只反映 `qwen3-max` 这一个模型的表现，换模型分数会变，不能当成"这个架构设计"普适性的证明。

## 5. Step 骨架（草案，需用六家真实源码校准后再定稿）

一步一个新能力，不合并：

| Step | 新增能力 | 备注 |
|---|---|---|
| 0 | 纯 chat，单次 completion | Oracle 模式跑 SWE-bench 基线分 |
| 1 | agent loop + 全能 `bash`/`exec` 工具 | ls/cat/grep/sed/跑测试全靠它；**第一次出现真正意义上的自主探索**，也是第一次出现非 oracle 的常规子集分数 |
| 2 | 拆出专用 `edit`（str_replace 风格） | 对照"专用编辑工具 vs 靠 bash sed/heredoc 改文件"，对应 ACI 论文的核心论点 |
| 3 | 拆出专用 `read_file`/`view`（带行号/窗口） | 替代 `cat` |
| 4 | 拆出专用 `search`/`grep`（结构化检索） | 从"靠 bash grep"升级 |
| 5 | Todo/Plan 追踪机制 | 对照 Claude Code 的 TodoWrite |
| 6 | 上下文管理（system prompt 精修 + 长对话 compaction） | 应对真实 issue 常见的长交互 |
| 7 | Sub-agent / 并行工具调用 | 对照 Claude Code 的 Task、Kimi CLI 的 subagent |
| 8 | 权限/审批 + sandbox | 对照 Codex 的 approval modes |
| 9 | 收尾：系统提示词整体调优 + SWE-bench Verified 全量（自研系统）+ 六家架构横向对比（不实跑） | |

设计要点：先给全能 bash（Codex 哲学的起点），再逐步拆出专用工具，刻意复现"大锤子 → 专用工具"的教学冲击力，而不是反过来。

## 6. 模型策略

- **全程单一模型**：`qwen3-max`，通过 `code.ai.cs.ac.cn` 网关调用（`.env` 里的 `OPENAI_BASE_URL`/`OPENAI_API_KEY`，变量名有历史遗留、实际是网关通用 key）。自研 9 步系列从 step 0 到收尾全部只用这一个模型，控制变量，保证分数变化只反映架构差异。
- **接入方式**：litellm 实测确认网关说的是 **Anthropic Messages API**（`/v1/messages`），不是 OpenAI Chat Completions——调用要用 `model="anthropic/qwen3-max"` + 显式传 `api_base`/`api_key`，OpenAI 风格 provider 前缀在路由层面对这把 key 直接 404。已封装进 `common/llm.py`。
- **为什么不是 Qwen3-Coder-Next**：原计划走阿里云百炼 Coding Plan 订阅 Qwen3-Coder-Next，现在改用现成网关后，网关里**没有任何 Qwen-Coder 系列模型**（`/v1/models` 列出 31 个模型，真实调用也确认过），只有通用款 `qwen3-max`/`qwen3.6-plus`，取前者。
  - 已知局限（需在教程中写出）：`qwen3-max` 非 coder 专精模型，repo 级理解/工具调用稳定性预期弱于 Qwen3-Coder-Next，曲线绝对值不能拿来和 Qwen 官方 coder 系列的公开分数直接对比。
- **六家参考 agent 不配模型**：范围已简化为仅架构对比、不实跑（见第 3 节），所以不需要为 Kimi CLI / Qwen Code 等分别接入原生模型。网关上 `kimi-k2.5`、`glm-4.6`、`deepseek-v4-flash` 等也验证过可用，但目前不接入代码，如后续要恢复实跑对比可以直接复用这次的探测结果。

## 7. Repo 结构

- **每步一个独立文件夹**（`src/agent_ladder/steps/step_0_bare_chat/`、`src/agent_ladder/steps/step_1_bash/`、……），而不是 git tag/分支。
  - 理由：GitHub 网页浏览时文件夹比 tag 更易点开阅读；`diff -r steps/step_N/ steps/step_N+1/` 能达到和 `git diff tag..tag` 类似的效果。
  - **2026-07-21 变更**：早期理由里还有一条"读者不需要懂 git/Python 包机制，直接 `cd` 进某个根级文件夹（如 `step-0-bare-chat/`）跑脚本"。后来因为自有代码分散在 `step-0-bare-chat/`、`scripts/`、`src/agent_ladder/` 三处、边界越来越乱，改成全部收进 `src/agent_ladder/` 一个 src-layout 包统一管理，step 目录挪到 `src/agent_ladder/steps/step_0_bare_chat/` 之类的路径，运行方式也变成 `uv run python -m agent_ladder.steps.step_0_bare_chat.run`，不再是单纯 `cd` 进文件夹跑脚本那么零门槛。这是用"统一 import/打包体系"换掉了一部分"cd 就能跑"的简单性，如果读者上手门槛因此变高，这个取舍可以重新讨论。
- **区分两类代码**：
  - **教学核心代码**（agent loop、当前步骤新加的工具）：**完整复制**到每个 step 目录，自成一体、从头读到尾即可看懂，不跳转到基类。复制本身就是教学价值的一部分。
  - **非教学的基础设施**：按关注点分包放在 `src/agent_ladder/` 下（src-layout，可编辑安装）——`shared/`（跨 step 复用但非教学重点，如 `llm.py`）、`benchmarks/swebench/`（SWE-bench 数据集/仓库检出缓存/固定子集，如 `dataset.py`、`repo.py`、`swebench_lite_30.json`）、`scripts/`（仓库维护脚本，如 `select_subset.py`）。避免同一个 bug 要在 10 个地方改。
- **测试**：`tests/`，用 pytest。真实调用网关的用例打 `@pytest.mark.integration`，`pyproject.toml` 里 `addopts = "-m 'not integration'"` 让默认 `pytest` 跳过、`pytest -m integration` 显式跑；`testpaths = ["tests"]` 避免误扫到 `reference-agents/` 里几家项目自己的测试。

## 8. 文档语言

- 先产出**中文**，之后用 AI 翻译成英文双语版。语言问题不卡主线进度。

## 9. 尚待执行（非共识内容，仅记录下一步）

- [x] 克隆参考仓库到 `reference-agents/`：`claude-code`（泄露 prompt）、`codex`、`kimi-cli`、`swe-agent`、`mini-swe-agent`（额外加的，100 行纯 bash agent，SWE-bench Verified 74%+，和 step 1 设计哲学高度对应）、`trae-agent`、`qwen-code`、`hermes-agent`；Python 项目（kimi-cli/swe-agent/mini-swe-agent/trae-agent/hermes-agent）已用 `uv sync` 建好 `.venv`
- [x] 用 `.env` 里的 `code.ai.cs.ac.cn` 网关跑通 `litellm.completion()`：确认协议是 Anthropic Messages API（`anthropic/` provider 前缀）、网关无 Qwen-Coder 系列、`kimi-k2.5`/`qwen3-max`/`glm`/`deepseek` 均可用、claude 系列余额受限打不了；第 6 节已按此更新
- [x] `src/agent_ladder/llm.py` 已封装好 `anthropic/` + `api_base`/`api_key` 调用方式，范围简化为**只保留 `qwen3-max`**（六家对比不再实跑，见第 3/6 节）；改成 src-layout + `uv` 可编辑安装，连通性检查从一次性脚本升级成 `tests/test_llm.py`（`@pytest.mark.integration`，见第 7 节）
- [x] 30 条固定子集：`src/agent_ladder/scripts/select_subset.py`（stratified，12 仓库，seed=42）生成 `src/agent_ladder/benchmarks/swebench/swebench_lite_30.json`；顺带发现第 4 节原写的"11 个仓库"是笔误，实测是 12 个，已修正
- [x] `src/agent_ladder/benchmarks/swebench/repo.py`：SWE-bench 官方 repo mirror 的本地检出缓存（clone + checkout base_commit），跨 step 共用（step 0 读文件内容用它，之后 step 1+ 给 agent 当工作目录也用它）
- [x] `src/agent_ladder/benchmarks/swebench/dataset.py`：按 `swebench_lite_30.json` 过滤出固定子集
- [x] `src/agent_ladder/steps/step_0_bare_chat/oracle.py`：oracle prompt 构造（照抄 SWE-bench 官方 "style-2" 模板文本，没直接 `import swebench.inference...`——那条 import 链会拖出不需要的 `transformers` 依赖）；单实例（`pallets__flask-4045`）人工验证过：prompt 正确包含 README + gold patch 改动的文件
- [x] `src/agent_ladder/steps/step_0_bare_chat/run.py`：跑子集、调 `qwen3-max`、用 `swebench` 自带的 `extract_diff`/`extract_minimal_patch` 抽取 patch、写 `predictions.jsonl`；单实例跑通，模型定位对了文件但 patch 格式不完全干净（预期内，第 2 步专用 `edit` 工具要解决的正是这个）
- [ ] **当前进行中**：30 条批量跑（后台任务，需要 clone 12 个仓库 + 30 次真实调用）
- [ ] **卡在 Docker**：评测脚本要接 `swebench.harness.run_evaluation`（CLI：`-p predictions.jsonl -d princeton-nlp/SWE-bench_Lite -i <30个instance_id> --run_id step-0 --namespace swebench`），这一步需要 Docker 才能跑（本机是 WSL2、没开 systemd，装 Docker Engine 的命令已经在对话里给过）；装完之前只能把命令/脚本写好，不能验证
- [ ] `src/agent_ladder/steps/step_0_bare_chat/README.md`
- [ ] 派 agent 并行读 `reference-agents/` 下几家源码，校准第 5 节的 step 顺序与工具颗粒度（延后，不阻塞先跑通调用）
