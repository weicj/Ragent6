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
