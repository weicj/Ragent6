# Ragent6 中文说明

<p align="right">
  <a href="README.md">English</a> | 简体中文
</p>

Ragent6 是一个面向 Agent 模型的本地确定性测评基准。它测试模型在弱工具环境中是否能够读证据、写文件、修改代码、执行本地检查、遵守安全边界、从错误中恢复，并完成多约束推理任务。

当前稳定版本：`1.1.0`。

说明：本文件只是中文说明文档。Ragent6 的默认公开题库、模型可见 prompt、manifest、checker 和运行输出均保持英文，以便作为国际通用版本发布。

## 测什么

Ragent6 1.1.0 一共 60 题，分为 6 个公开维度，每个维度 10 题。

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

纯 0/1 会把“任务核心做对但有小瑕疵”和“完全没完成”混在一起。Ragent6 1.1.0 采用确定性 partial scoring：严格通过给满分；严格失败时，只对 trace 中可验证的子目标给部分分；危险行为可以封顶或归零。

这使榜单更能区分模型在真实 Agent 场景下的能力差异。

## 快速自检

```bash
cd Ragent6
python3 scripts/run_eval.py \
  --manifest manifests/ragent6.json \
  --adapter mock \
  --out results/mock-1.1.0
```

预期输出：

```text
Ragent6 1.1.0: 60/60 (invalid=0)
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
  --manifest manifests/ragent6.json \
  --adapter native_local \
  --out results/by-model/local-model/1.1.0/run-001
```

native harness 在题目允许时只暴露四个极简工具：

- `read`
- `write`
- `edit`
- `exec`

## 计算成绩

创建一个 metadata 文件列出结果目录，可参考 `examples/model_metadata.example.json`。
本地归档推荐使用 `results/by-model/<model-slug>/<suite-version>/<run-id>/`。

```bash
python3 scripts/score_results.py \
  --metadata examples/model_metadata.example.json \
  --out-json results/ragent6_scores.json \
  --report reports/ragent6_scores.md
```

## 发布前审计

```bash
python3 scripts/release_audit.py \
  --manifest manifests/ragent6.json \
  --suite-version 1.1.0
```

发布榜单前应确认：

- 使用 `Ragent6 1.1.0` manifest。
- 每个模型都完成 60 题。
- `invalid_cases == 0`。
- 关闭 hidden thinking/reasoning。
- 使用温度 0 或服务端支持的最接近确定性设置。
- 保留每题的 `trace.json` 和 `case_result.json`，以便复算和审计。

## 版本规则

- Patch 版本，例如 `1.1.x`：只允许文档、报告格式、非评分 CLI 修复，不改变分数。
- Minor 版本，例如 `1.x.0`：题目、checker、scorer、权重、维度或工具协议变更，可能改变分数。
- `2.0.0`：方法论级重构。

不同 minor 版本的分数不应混在同一榜单中，除非明确标注版本。

## 文档入口

- `README.md`：英文主说明。
- `METHODOLOGY.md`：英文方法论和复现规则。
- `docs/CASES.md`：60 题公开目录。
- `docs/VERSIONING.md`：版本兼容规则。
- `docs/RELEASE_CHECKLIST.md`：发布检查清单。
- `results/by-model/README.md`：按模型归档本地测试结果的推荐目录规范。
