# Ragent6

<p align="right">
  English | <a href="README.zh-CN.md">简体中文</a>
</p>

Ragent6 is a deterministic, local benchmark for agent-capable language models. It tests whether a model can operate inside a weak tool harness, read evidence, write or edit files, run local checks, obey safety boundaries, recover from errors, and solve multi-constraint reasoning tasks.

Current release version: `0.2.0`.

Status: `0.2.0` is the active pre-1.0 public score line. Earlier `1.0.0` and `1.1.0` labels were promoted too early and should be treated as historical calibration score lines, not stable public releases.

Ragent6 now has two locale score lines under the same methodology:

- `en-US`: international default, English prompts and English harness instructions.
- `zh-CN`: Chinese local benchmark line, Chinese prompts and Chinese harness instructions.

Do not mix `en-US` and `zh-CN` results in the same leaderboard.

## What It Measures

Ragent6 `0.2.0` contains 60 cases across 6 public dimensions. Each dimension has 10 cases.

| Dimension | Name | Weight | What It Tests |
| --- | --- | ---: | --- |
| R1 | Task Closure | 20 | Complete task execution from goal understanding to artifact and verification. |
| R2 | Evidence Use | 18 | Evidence retrieval, precedence, long-context lookup, and grounded answers. |
| R3 | Format Control | 12 | Machine-consumable JSON, diffs, command plans, and labeled outputs. |
| R4 | Safety Boundary | 16 | Refusal or guarding of dangerous actions, offline constraints, dry-run behavior, and scope control. |
| R5 | Error Recovery | 14 | Multi-turn correction, stale evidence handling, invalid-output repair, and state updates. |
| R6 | Complex Reasoning | 20 | Causal chains, counterfactuals, decoys, policy selection, and deep state tracking. |

## Scoring

Ragent6 reports two scores:

- `partial_weighted`: the primary deterministic partial score, weighted to 100.
- `strict_raw`: the auxiliary strict pass count, reported as `x/60`.

Partial scoring is deterministic and uses only local trace evidence, checker outputs, tool calls, file snapshots, and final answers. It does not use an LLM judge.

Safety hard violations still receive zero credit.

## Run The Mock Smoke Test

```bash
cd Ragent6
python3 scripts/run_eval.py \
  --manifest manifests/ragent6_0_2_0_en_US.json \
  --adapter mock \
  --out results/mock-0.2.0-en-US
```

Expected result:

```text
Ragent6 0.2.0 en-US: 60/60 (invalid=0)
```

## Run A Local Model

Start any OpenAI-compatible chat completions server first. For llama.cpp, disable hidden reasoning or thinking for comparable results.

Example llama.cpp flags:

```bash
-rea off --reasoning-budget 0 --chat-template-kwargs '{"enable_thinking":false}'
```

Then run:

```bash
cd Ragent6
export RAGENT6_BASE_URL=http://127.0.0.1:8080/v1
export RAGENT6_MODEL_ID=local-model
export RAGENT6_MAX_TOKENS=2048
export RAGENT6_AGENT_TIMEOUT=180

python3 scripts/run_eval.py \
  --manifest manifests/ragent6_0_2_0_en_US.json \
  --adapter native_local \
  --out results/by-model/local-model/0.2.0/en-US/run-001
```

The native harness exposes four tools to the model when a case allows them:

- `read`
- `write`
- `edit`
- `exec`

## Compute Partial Scores

Create a metadata file listing result directories. See `examples/model_metadata.example.json`.
For local archives, the recommended layout is `results/by-model/<model-slug>/<suite-version>/<locale>/<run-id>/`.

```bash
python3 scripts/score_results.py \
  --metadata examples/model_metadata.example.json \
  --out-json results/ragent6_scores.json \
  --report reports/ragent6_scores.md
```

## zh-CN Reference Scores

The table below is the current local `zh-CN` reference panel, run with the no-thinking native harness. `Score` is the deterministic partial weighted score out of 100, `Passes` is the auxiliary strict `x/60` pass count, and each R1-R6 column is a 10-point partial dimension score. These scores are for the Chinese locale only and must not be mixed with the `en-US` leaderboard.

| Rank | Base | Size | Variant | Quant | Score | Passes | R1 Closure | R2 Evidence | R3 Format | R4 Safety | R5 Recovery | R6 Reasoning |
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

## Audit Release Assets

```bash
python3 scripts/release_audit.py \
  --manifest manifests/ragent6_0_2_0_en_US.json \
  --suite-version 0.2.0 \
  --locale en-US
```

## Documentation

- `METHODOLOGY.md`: scoring policy and reproducibility rules.
- `docs/CASES.md`: public 60-case catalog.
- `docs/LOCALES.md`: locale score-line policy.
- `docs/VERSIONING.md`: compatibility and version bump rules.
- `docs/RELEASE_CHECKLIST.md`: validation checklist before publishing results.
- `results/by-model/README.md`: recommended local layout for per-model result archives.

## Versioning

- Patch versions: documentation, reporting, or harness fixes that do not change scores.
- New score lines: case, checker, scorer, weight, locale prompt, or dimension changes that can change scores.
- Locale score lines: same suite version but different `locale`; results are not directly comparable across locales.
- `1.0.0`: reserved for the first frozen public release.

Earlier experimental branches are intentionally not included in this clean repository. Their only lineage is preserved inside `docs/case_map.json`.
