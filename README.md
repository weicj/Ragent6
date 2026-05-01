# Ragent6

Ragent6 is a deterministic, local benchmark for agent-capable language models. It tests whether a model can operate inside a weak tool harness, read evidence, write or edit files, run local checks, obey safety boundaries, recover from errors, and solve multi-constraint reasoning tasks.

Current stable version: `1.1.0`.

## What It Measures

Ragent6 1.1.0 contains 60 cases across 6 public dimensions. Each dimension has 10 cases.

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
  --manifest manifests/ragent6.json \
  --adapter mock \
  --out results/mock-1.1.0
```

Expected result:

```text
Ragent6 1.1.0: 60/60 (invalid=0)
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
  --manifest manifests/ragent6.json \
  --adapter native_local \
  --out results/local-model-ragent6
```

The native harness exposes four tools to the model when a case allows them:

- `read`
- `write`
- `edit`
- `exec`

## Compute Partial Scores

Create a metadata file listing result directories. See `examples/model_metadata.example.json`.

```bash
python3 scripts/score_results.py \
  --metadata examples/model_metadata.example.json \
  --out-json results/ragent6_scores.json \
  --report reports/ragent6_scores.md
```

## Audit Release Assets

```bash
python3 scripts/release_audit.py \
  --manifest manifests/ragent6.json \
  --suite-version 1.1.0
```

## Documentation

- `METHODOLOGY.md`: scoring policy and reproducibility rules.
- `docs/CASES.md`: public 60-case catalog.
- `docs/VERSIONING.md`: compatibility and version bump rules.
- `docs/RELEASE_CHECKLIST.md`: validation checklist before publishing results.

## Versioning

- Patch versions, such as `1.1.x`: documentation, reporting, or harness fixes that do not change scores.
- Minor versions, such as `1.x.0`: case, checker, scorer, weight, or dimension changes that can change scores.
- `2.0.0`: major methodology redesign.

Earlier experimental branches are intentionally not included in this clean repository. Their only lineage is preserved inside `docs/case_map.json`.
