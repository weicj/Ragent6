# Versioning

Ragent6 public benchmark versioning starts at `0.2.0`.

## Current Line

The active line is `0.2.0`, the first public Ragent6 benchmark release.

`0.2.0` has two prompt sets:

- `en-US`
- `zh-CN`

Score reports should state which prompt set was used.

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
