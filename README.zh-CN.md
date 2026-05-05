# Ragent6 中文说明

<p align="right">
  <a href="README.md">English</a> | 简体中文
</p>

Ragent6 是一个面向 Agent 模型的本地确定性测评基准。它测试模型在弱工具环境中是否能够读证据、写文件、修改代码、执行本地检查、遵守安全边界、从错误中恢复，并完成多约束推理任务。

当前发布版本：英文 `0.2.0`；中文 prompt set `0.2.1`。

状态：`0.2.0` 是首个公开测评版本；`zh-CN 0.2.1` 是清理英文残留后的中文题面版本。

说明：Ragent6 在同一方法论、case ID、fixtures 和 checker 下提供英文和中文两套 prompt。

## 测什么

Ragent6 当前公开线一共 60 题，分为 6 个公开维度，每个维度 10 题。

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
  --manifest manifests/ragent6_0_2_1_zh_CN.json \
  --adapter mock \
  --out results/mock-0.2.1-zh-CN
```

预期输出：

```text
Ragent6 0.2.1 zh-CN: 60/60 (invalid=0)
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
  --manifest manifests/ragent6_0_2_1_zh_CN.json \
  --adapter native_local \
  --out results/by-model/local-model/0.2.1/zh-CN/run-001
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

## 实测参考成绩

下面是已经完成的 `zh-CN 0.2.0` 本地实测面板，使用 no-thinking native harness；总分为 deterministic partial 加权分，满分 100；通过项为 strict `x/60`。维度列为各维度 partial 子分，每项满分 10。`zh-CN 0.2.1` 清理了中文题面中的英文残留，发布新榜单前应重新跑分。

| 排名 | 底座 | 参数量 | 变体 | 量化 | 总分 | 通过项 | 任务闭环 | 证据取用 | 格式规范 | 安全边界 | 错误恢复 | 复杂推理 |
| ---: | --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Qwen3.6 | 27B | Qwopus Abliterated | Q4_K_M | 92.3 | 51/60 | 9.1 | 7.8 | 9.5 | 9.8 | 9.7 | 9.9 |
| 2 | Qwen3.6 | 27B | Qwopus Preview | Q4_K_M | 89.4 | 48/60 | 9.1 | 7.4 | 9.7 | 8.9 | 9.3 | 9.5 |
| 3 | Qwen3.6 | 27B | Unsloth IT | Q4_K_M | 87.4 | 49/60 | 9.1 | 7.8 | 9.7 | 8.9 | 9.3 | 8.2 |
| 4 | Qwen3.6 | 27B | Carnice V2 | Q4_K_M | 86.4 | 43/60 | 9.1 | 7.4 | 9.1 | 9.8 | 8.2 | 8.4 |
| 5 | Qwen3.6 | 35B A3B | Unsloth IT | Q4_K_M | 79.9 | 38/60 | 8.1 | 6.8 | 7.8 | 8.8 | 8.6 | 8.1 |
| 6 | Qwen3.5 | 27B | Unsloth IT | Q4_K_M | 76.7 | 37/60 | 8.3 | 5.3 | 9.4 | 7.7 | 8.6 | 7.5 |
| 7 | Qwen3.6 | 35B A3B | Hauhau | IQ4_XS | 76.6 | 37/60 | 8.1 | 6.9 | 9.1 | 5.1 | 8.8 | 8.3 |
| 8 | Gemma 4 | 31B | Unsloth IT | Q4_K_M | 74.7 | 37/60 | 8.3 | 8.1 | 9.0 | 6.3 | 9.3 | 4.8 |
| 9 | Gemma 4 | 26B A4B | Gemopus Preview | Q4_K_M | 72.1 | 34/60 | 8.3 | 7.2 | 8.2 | 5.7 | 8.9 | 5.5 |
| 10 | Qwen3.5 | 9B | CoPaw Flash | Q4_K_M | 67.7 | 30/60 | 5.1 | 4.7 | 8.7 | 6.6 | 8.2 | 8.3 |
| 11 | Gemma 4 | 26B A4B | Unsloth IT | Q4_K_M | 67.2 | 30/60 | 8.3 | 6.1 | 8.4 | 4.9 | 8.9 | 4.5 |
| 12 | Qwen3.5 | 35B A3B | Unsloth IT | Q4_K_M | 63.2 | 28/60 | 4.0 | 3.6 | 9.1 | 7.2 | 7.0 | 8.3 |
| 13 | Gemma 4 | E4B | Hauhau | Q5_K_M | 61.8 | 27/60 | 6.6 | 5.0 | 7.7 | 6.3 | 7.6 | 4.9 |
| 14 | Gemma 4 | E4B | Unsloth IT | Q5_K_M | 61.5 | 28/60 | 5.7 | 6.2 | 7.3 | 6.1 | 7.7 | 4.9 |
| 15 | Qwen3.5 | 9B | Carnice | Q4_K_M | 58.6 | 23/60 | 4.9 | 4.6 | 8.4 | 6.8 | 6.5 | 5.3 |
| 16 | Qwen3.5 | 13B | Heretic | IQ4_XS | 58.4 | 23/60 | 4.8 | 4.7 | 7.5 | 6.1 | 7.5 | 5.5 |
| 17 | Qwen3.5 | 18B | Qwopus GLM | Q4_K_M | 57.2 | 27/60 | 4.0 | 3.5 | 9.7 | 4.8 | 6.8 | 7.0 |
| 18 | Qwen3.5 | 9B | Unsloth IT | Q4_K_M | 56.8 | 24/60 | 5.1 | 3.3 | 8.2 | 6.3 | 8.1 | 4.7 |
| 19 | Qwen3.5 | 9B | Qwopus v3 | Q4_K_M | 56.6 | 25/60 | 2.8 | 5.7 | 8.5 | 5.5 | 6.7 | 6.1 |
| 20 | Qwen3.5 | 9B | A3 i1 | IQ4_NL | 54.7 | 19/60 | 4.1 | 4.7 | 6.5 | 7.3 | 6.6 | 4.5 |
| 21 | Qwen3.5 | 4B | OpenResearchTools | Q4_K_M | 52.1 | 19/60 | 2.3 | 4.1 | 7.5 | 3.2 | 7.3 | 7.8 |
| 22 | Gemma 4 | E2B | Unsloth IT | Q4_K_M | 49.6 | 18/60 | 3.3 | 4.4 | 6.1 | 4.5 | 6.5 | 5.8 |
| 23 | Qwen3 | 8B | Unsloth IT | Q4_K_M | 45.6 | 18/60 | 4.0 | 4.0 | 8.8 | 2.5 | 6.8 | 3.2 |
| 24 | Gemma 3n | E4B | Unsloth IT | Q4_K_M | 43.7 | 14/60 | 1.4 | 3.2 | 5.7 | 7.2 | 5.6 | 4.5 |
| 25 | Qwen3 | 4B | Unsloth IT | Q4_K_M | 40.3 | 14/60 | 4.0 | 3.7 | 7.1 | 2.1 | 6.3 | 2.5 |
| 26 | Gemma 4 | E4B | Gemopus Preview | IQ4_XS | 39.2 | 11/60 | 1.7 | 2.8 | 6.1 | 5.2 | 5.2 | 3.9 |
| 27 | Qwen3.5 | 2B | Unsloth IT | Q4_K_M | 36.6 | 10/60 | 2.5 | 3.9 | 5.1 | 4.1 | 5.2 | 2.4 |
| 28 | Gemma 3n | E2B | Unsloth IT | Q4_K_M | 35.7 | 8/60 | 1.3 | 3.4 | 6.8 | 4.3 | 5.6 | 2.1 |
| 29 | Qwen3.5 | 2B | AaryanK | Q4_K_M | 34.2 | 8/60 | 2.5 | 2.8 | 5.2 | 4.7 | 5.5 | 1.3 |
| 30 | Squeez | 2B | i1 | Q4_K_M | 30.5 | 7/60 | 2.0 | 2.6 | 5.5 | 4.0 | 4.6 | 1.3 |
| 31 | LFM2.5 | 350M | base | Q5_K_M | 20.7 | 2/60 | 1.0 | 1.7 | 3.3 | 2.9 | 4.1 | 0.7 |
| 32 | LFM2.5 | 1.2B | Instruct | Q4_K_M | 18.5 | 4/60 | 0.7 | 1.3 | 2.9 | 3.0 | 3.7 | 0.7 |

注：以上参考成绩使用历史 `zh-CN 0.2.0` 中文表单测试，不应与 `zh-CN 0.2.1` 新结果混榜。

## 发布前审计

```bash
python3 scripts/release_audit.py \
  --manifest manifests/ragent6_0_2_1_zh_CN.json \
  --suite-version 0.2.1 \
  --locale zh-CN
```

发布榜单前应确认：

- 使用对应的 `Ragent6` manifest，并明确 `suite_version` 与 `locale`。
- 每个模型都完成 60 题。
- `invalid_cases == 0`。
- 关闭 hidden thinking/reasoning。
- 使用温度 0 或服务端支持的最接近确定性设置。
- 保留每题的 `trace.json` 和 `case_result.json`，以便复算和审计。

## 版本规则

- Patch 版本：只允许文档、报告格式、非评分 CLI 修复，不改变分数。
- 新 benchmark version：题目、checker、scorer、权重、维度、prompt set 或工具协议变更，可能改变分数。
- Ragent6 公开版本从 `0.2.0` 开始。

## 文档入口

- `README.md`：英文主说明。
- `METHODOLOGY.md`：英文方法论和复现规则。
- `docs/CASES.md`：60 题公开目录。
- `docs/LOCALES.md`：prompt set 说明。
- `docs/VERSIONING.md`：版本兼容规则。
- `docs/RELEASE_CHECKLIST.md`：发布检查清单。
- `results/by-model/README.md`：按模型归档本地测试结果的推荐目录规范。
