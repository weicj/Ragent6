# Ragent6 中文说明

<p align="right">
  <a href="README.md">English</a> | 简体中文
</p>

Ragent6 是一个面向 Agent 模型的本地确定性测评基准。它测试模型在弱工具环境中是否能够读证据、写文件、修改代码、执行本地检查、遵守安全边界、从错误中恢复，并完成多约束推理任务。

当前发布版本：`0.2.0`。

状态：`0.2.0` 是当前可发布的 pre-1.0 公开 score line。此前 `1.0.0` 和 `1.1.0` 进入正式版本过早，现在只作为历史校准 score line 保留，不作为稳定公开版本。

说明：Ragent6 现在同时维护两个语言口径：`en-US` 面向国际通用用户，`zh-CN` 面向中文本地 Agent 场景。两个口径共享同一方法论、case ID、fixtures 和 checker，但 prompt 与 harness 指令按语言分开，成绩不能混榜。

## 测什么

Ragent6 `0.2.0` 一共 60 题，分为 6 个公开维度，每个维度 10 题。

| 维度 | 英文名称 | 中文说明 | 权重 | 测试重点 |
| --- | --- | --- | ---: | --- |
| R1 | Task Closure | 任务闭环 | 20 | 从理解目标到生成产物、验证产物、给出最终答案的完整执行能力。 |
| R2 | Evidence Use | 证据取用 | 18 | 本地搜索、读文件、证据优先级、长上下文定位和基于证据的回答。 |
| R3 | Format Control | 格式控制 | 12 | 严格 JSON、diff、命令序列、固定标签输出等机器可消费格式。 |
| R4 | Safety Boundary | 安全边界 | 16 | 面对危险操作、离线限制、prompt injection、生产风险时的安全行为。 |
| R5 | Error Recovery | 错误恢复 | 14 | 路径错误、测试失败、后续纠正、旧证据失效、状态更新等恢复能力。 |
| R6 | Complex Reasoning | 复杂推理 | 20 | 多跳因果链、反事实、干扰项、策略选择和深层状态追踪。 |

## 分数口径

Ragent6 输出两个核心指标：

- `partial_weighted`：主分数，确定性 partial score，加权到 100 分。
- `strict_raw`：辅助指标，严格通过题数，格式为 `x/60`。

主分数不使用 LLM judge。它只依赖本地 trace、checker 输出、工具调用、文件快照和最终答案。安全硬违规仍然记 0 分。

## 为什么不是纯 0/1

纯 0/1 会把“任务核心做对但有小瑕疵”和“完全没完成”混在一起。Ragent6 `0.2.0` 采用确定性 partial scoring：严格通过给满分；严格失败时，只对 trace 中可验证的子目标给部分分；危险行为可以封顶或归零。

这使榜单更能区分模型在真实 Agent 场景下的能力差异。

## 快速自检

```bash
cd Ragent6
python3 scripts/run_eval.py \
  --manifest manifests/ragent6_0_2_0_zh_CN.json \
  --adapter mock \
  --out results/mock-0.2.0-zh-CN
```

预期输出：

```text
Ragent6 0.2.0 zh-CN: 60/60 (invalid=0)
```

## 测本地模型

先启动一个 OpenAI-compatible chat completions 服务。为了可比性，应关闭模型隐藏 thinking 或 reasoning。

llama.cpp 示例参数：

```bash
-rea off --reasoning-budget 0 --chat-template-kwargs '{"enable_thinking":false}'
```

然后运行：

```bash
cd Ragent6
export RAGENT6_BASE_URL=http://127.0.0.1:8080/v1
export RAGENT6_MODEL_ID=local-model
export RAGENT6_MAX_TOKENS=2048
export RAGENT6_AGENT_TIMEOUT=180

python3 scripts/run_eval.py \
  --manifest manifests/ragent6_0_2_0_zh_CN.json \
  --adapter native_local \
  --out results/by-model/local-model/0.2.0/zh-CN/run-001
```

native harness 在题目允许时只暴露四个极简工具：

- `read`
- `write`
- `edit`
- `exec`

## 计算成绩

创建一个 metadata 文件列出结果目录，可参考 `examples/model_metadata.example.json`。
本地归档推荐使用 `results/by-model/<model-slug>/<suite-version>/<locale>/<run-id>/`。

```bash
python3 scripts/score_results.py \
  --metadata examples/model_metadata.example.json \
  --out-json results/ragent6_scores.json \
  --report reports/ragent6_scores.md
```

## 中文口径实测参考成绩

下面是当前已完成的中文口径本地实测面板，使用 no-thinking native harness；总分为 deterministic partial 加权分，满分 100；通过项为 strict `x/60`。这些结果只代表中文测试口径，不能和 `en-US` 国际口径混榜。后续正式公开榜单应按 `0.2.0 zh-CN` manifest 重新归档或复算。

| 排名 | 底座 | 参数量 | 变体 | 量化 | 总分 | 通过项 |
| ---: | --- | --- | --- | --- | ---: | --- |
| 1 | Qwen3.6 | 27B | Qwopus Abliterated | Q4_K_M | 92.3 | 51/60 |
| 2 | Qwen3.6 | 27B | Qwopus Preview | Q4_K_M | 89.4 | 48/60 |
| 3 | Qwen3.6 | 27B | Unsloth IT | Q4_K_M | 87.4 | 49/60 |
| 4 | Qwen3.6 | 27B | Carnice V2 | Q4_K_M | 86.4 | 43/60 |
| 5 | Qwen3.6 | 35B A3B | Unsloth IT | Q4_K_M | 79.9 | 38/60 |
| 6 | Qwen3.5 | 27B | Unsloth IT | Q4_K_M | 76.7 | 37/60 |
| 7 | Qwen3.6 | 35B A3B | Hauhau | IQ4_XS | 76.6 | 37/60 |
| 8 | Gemma 4 | 31B | Unsloth IT | Q4_K_M | 74.7 | 37/60 |
| 9 | Gemma 4 | 26B A4B | Gemopus Preview | Q4_K_M | 72.1 | 34/60 |
| 10 | Qwen3.5 | 9B | CoPaw Flash | Q4_K_M | 67.7 | 30/60 |
| 11 | Gemma 4 | 26B A4B | Unsloth IT | Q4_K_M | 67.2 | 30/60 |
| 12 | Qwen3.5 | 35B A3B | Unsloth IT | Q4_K_M | 63.2 | 28/60 |
| 13 | Gemma 4 | E4B | Hauhau | Q5_K_M | 61.8 | 27/60 |
| 14 | Gemma 4 | E4B | Unsloth IT | Q5_K_M | 61.5 | 28/60 |
| 15 | Qwen3.5 | 9B | Carnice | Q4_K_M | 58.6 | 23/60 |
| 16 | Qwen3.5 | 13B | Heretic | IQ4_XS | 58.4 | 23/60 |
| 17 | Qwen3.5 | 18B | Qwopus GLM | Q4_K_M | 57.2 | 27/60 |
| 18 | Qwen3.5 | 9B | Unsloth IT | Q4_K_M | 56.8 | 24/60 |
| 19 | Qwen3.5 | 9B | Qwopus v3 | Q4_K_M | 56.6 | 25/60 |
| 20 | Qwen3.5 | 9B | A3 i1 | IQ4_NL | 54.7 | 19/60 |
| 21 | Qwen3.5 | 4B | OpenResearchTools | Q4_K_M | 52.1 | 19/60 |
| 22 | Gemma 4 | E2B | Unsloth IT | Q4_K_M | 49.6 | 18/60 |
| 23 | OpenNemo Cascade2 | 30B A3B | i1 | Q5_K_M | 46.3 | 15/60 |
| 24 | Qwen3 | 8B | Unsloth IT | Q4_K_M | 45.6 | 18/60 |
| 25 | Gemma 3n | E4B | Unsloth IT | Q4_K_M | 43.7 | 14/60 |
| 26 | Qwen3 | 4B | Unsloth IT | Q4_K_M | 40.3 | 14/60 |
| 27 | Nemotron Cascade2 | 30B A3B | base | Q5_K_M | 39.9 | 14/60 |
| 28 | Gemma 4 | E4B | Gemopus Preview | IQ4_XS | 39.2 | 11/60 |
| 29 | Qwen3.5 | 2B | Unsloth IT | Q4_K_M | 36.6 | 10/60 |
| 30 | Gemma 3n | E2B | Unsloth IT | Q4_K_M | 35.7 | 8/60 |
| 31 | Qwen3.5 | 2B | AaryanK | Q4_K_M | 34.2 | 8/60 |
| 32 | Squeez | 2B | i1 | Q4_K_M | 30.5 | 7/60 |
| 33 | LFM2.5 | 350M | base | Q5_K_M | 20.7 | 2/60 |
| 34 | LFM2.5 | 1.2B | Instruct | Q4_K_M | 18.5 | 4/60 |

## 发布前审计

```bash
python3 scripts/release_audit.py \
  --manifest manifests/ragent6_0_2_0_zh_CN.json \
  --suite-version 0.2.0 \
  --locale zh-CN
```

发布榜单前应确认：

- 使用 `Ragent6 0.2.0` manifest，并明确 `locale`。
- 每个模型都完成 60 题。
- `invalid_cases == 0`。
- 关闭 hidden thinking/reasoning。
- 使用温度 0 或服务端支持的最接近确定性设置。
- 保留每题的 `trace.json` 和 `case_result.json`，以便复算和审计。

## 版本规则

- Patch 版本：只允许文档、报告格式、非评分 CLI 修复，不改变分数。
- 新 score line：题目、checker、scorer、权重、维度、locale prompt 或工具协议变更，可能改变分数。
- 语言口径：`en-US` 和 `zh-CN` 是同版本下的不同 locale score line，不能直接混榜。
- `1.0.0`：预留给第一个真正冻结的公开稳定版本。

不同 score line 或不同 locale 的分数不应混在同一榜单中。

## 文档入口

- `README.md`：英文主说明。
- `METHODOLOGY.md`：英文方法论和复现规则。
- `docs/CASES.md`：60 题公开目录。
- `docs/LOCALES.md`：语言口径和分榜规则。
- `docs/VERSIONING.md`：版本兼容规则。
- `docs/RELEASE_CHECKLIST.md`：发布检查清单。
- `results/by-model/README.md`：按模型归档本地测试结果的推荐目录规范。
