# Versioning

Ragent6 public benchmark versioning starts at `0.2.0`.

## Current Lines

The first public Ragent6 benchmark release is `0.2.0`.

Current public manifests:

- `en-US 0.2.0`: `manifests/ragent6_0_2_0_en_US.json`
- `zh-CN 0.2.2`: `manifests/ragent6_0_2_2_zh_CN.json`

`zh-CN 0.2.1` cleaned English remnants from the Chinese prompt files.

`zh-CN 0.2.2` continues the Chinese line with prompt, native-harness, and checker-equivalence adaptations for Chinese local runs. It keeps the same methodology, case IDs, fixtures, dimensions, and weights as `0.2.0`, but it is a new benchmark version because these changes can affect scores.

Score reports should state which benchmark version and prompt set were used.

## Compatible Patch Changes

Patch releases may be used only for changes that do not affect scores:

- README or documentation edits.
- Report formatting changes.
- Non-scoring CLI ergonomics.
- Bug fixes that only improve error reporting.

## New Benchmark Version

Use a new benchmark version when scores can change:

- Case prompt changes.
- Prompt set changes.
- Fixture changes.
- Checker changes.
- Partial scorer changes.
- Dimension or weight changes.
- Tool protocol changes.

## Major Redesign

Use a major version for methodology redesign:

- Different dimensions.
- Different number of cases.
- LLM judge integration.
- Non-local or online dependencies.
- A fundamentally different harness.
