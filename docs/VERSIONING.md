# Versioning

Ragent6 uses pre-1.0 score-line versioning until the benchmark is stable enough for public release.

## Current Line

The active line is `0.2.0`. Earlier `1.0.0` and `1.1.0` labels were promoted too early and are historical calibration lines only.

`0.2.0` has two locale score lines:

- `en-US`
- `zh-CN`

Locale results are not directly comparable and must not be mixed in one leaderboard.

## Compatible Patch Changes

Patch releases may be used only for changes that do not affect scores:

- README or documentation edits.
- Report formatting changes.
- Non-scoring CLI ergonomics.
- Bug fixes that only improve error reporting.

## New Score Line

Use a new `0.x.y` score line when scores can change:

- Case prompt changes.
- Locale prompt changes.
- Fixture changes.
- Checker changes.
- Partial scorer changes.
- Dimension or weight changes.
- Tool protocol changes.

## Stable Release

Reserve `1.0.0` for the first frozen public release. It should only be assigned after bridge calibration, score stability checks, documentation, and audit tooling are mature enough that downstream users can treat the benchmark as stable.

## Major Redesign

After a stable release exists, use a major version such as `2.0.0` for methodology redesign:

- Different dimensions.
- Different number of cases.
- LLM judge integration.
- Non-local or online dependencies.
- A fundamentally different harness.
