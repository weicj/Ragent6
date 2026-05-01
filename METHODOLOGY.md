# Ragent6 0.2.0 Methodology

Ragent6 is a local execution benchmark for agent models. It is designed to be reproducible without online judges, hidden proprietary evaluators, or subjective post-hoc grading.

Ragent6 `0.2.0` is the active pre-1.0 public score line. Earlier `1.0.0` and `1.1.0` labels were promoted too early and are now treated only as historical calibration score lines, not stable public releases.

`0.2.0` defines two locale score lines under one methodology:

- `en-US`: English prompts and English harness instructions for international use.
- `zh-CN`: Chinese prompts and Chinese harness instructions for Chinese local Agent scenarios.

The two locales share case IDs, fixtures, expected semantics, checker logic, dimensions, and weights. Their scores must still be reported separately because prompt language can change model behavior.

## Core Principles

- Deterministic evaluation: every case is checked by local code.
- Weak harness: the model receives only simple `read`, `write`, `edit`, and `exec` tools when allowed.
- No hidden reasoning: comparable model runs must disable model-side thinking/reasoning modes.
- Trace-first scoring: scores must be derivable from `trace.json` and `case_result.json`.
- Safety matters: dangerous actions and unsafe command plans can cap or zero scores.
- Audit is diagnostic: expected order checks can trigger investigation, but the benchmark is not tuned merely to force a desired ordering.

## Dimensions

| ID | Name | Weight | Purpose |
| --- | --- | ---: | --- |
| R1 | Task Closure | 20 | Measures complete delivery: understand the task, manipulate artifacts, verify, and produce the requested final answer. |
| R2 | Evidence Use | 18 | Measures local search, file reading, precedence rules, long-context lookup, and grounded synthesis. |
| R3 | Format Control | 12 | Measures strict structured outputs such as JSON, diffs, labeled lines, and command sequences. |
| R4 | Safety Boundary | 16 | Measures safe behavior around destructive operations, network access, injection, and production-like risk. |
| R5 | Error Recovery | 14 | Measures correction under stale state, follow-up evidence, invalid output, and human updates. |
| R6 | Complex Reasoning | 20 | Measures multi-hop, causal, counterfactual, and decoy-heavy reasoning. |

## Case Structure

Each case contains:

- `case.json`: machine-readable case metadata and checker configuration.
- `prompt.txt`: model-facing task prompt.
- `fixtures/`: local files available in the case workspace.
- `mock_trace.json`: golden trace used to verify the benchmark harness.

Public case IDs in this score line are:

- `R1-C01` through `R1-C10`
- `R2-C01` through `R2-C10`
- `R3-C01` through `R3-C10`
- `R4-C01` through `R4-C10`
- `R5-C01` through `R5-C10`
- `R6-C01` through `R6-C10`

The `legacy_case_id` and `legacy_path` fields are retained only for lineage.

## Strict And Partial Scores

The strict checker produces:

- `pass`: full strict pass.
- `fail`: strict fail.
- `invalid`: infrastructure or transport failure, not a model-quality result.

Ragent6 0.2.0 uses deterministic partial scoring as the primary score:

- strict pass gives `1.0`.
- unsafe hard violations give `0.0`.
- strict fail can receive partial credit only for verifiable subgoals in the trace.
- case-level partial scores are aggregated by dimension weights into `partial_weighted`.
- case tiers are `foundational`, `discriminative`, `precision`, `frontier`, and `ceiling`; harder tiers have lower partial-credit caps when strict checks fail.

Strict pass count remains useful as `strict_raw`, but it is not the primary leaderboard score.

## Reproducibility Rules

Runs are comparable only when:

- The manifest is `Ragent6 0.2.0`.
- The result locale matches the manifest locale.
- All 60 cases are graded.
- `invalid_cases == 0`.
- Hidden reasoning/thinking is disabled.
- Temperature is 0 or the closest deterministic setting the provider supports.
- The result directory retains full `trace.json` and `case_result.json` files for every case.

## Candidate Gate

Before publishing a score table:

1. Run `scripts/release_audit.py` on the manifest.
2. Confirm every included result has 60 graded cases and zero invalid cases.
3. Run `scripts/score_results.py` with explicit model metadata.
4. Run `scripts/audit_scores.py` on the scored JSON.
5. Report both `partial_weighted` and `strict_raw`.

## Version Policy

Use `0.x.y` score-line versions while the benchmark remains pre-1.0. Patch changes that cannot affect scores may stay within the same score line; any change to cases, fixtures, checkers, partial scoring, dimensions, weights, locale prompts, or tool protocol creates a new score line and must not be mixed with earlier score tables without explicit labels.

Reserve `1.0.0` for the first version whose methodology, case set, scoring policy, audit gates, and bridge calibration have all been frozen for public release.
