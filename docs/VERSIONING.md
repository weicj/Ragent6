# Versioning

Ragent6 uses semantic versioning for benchmark compatibility.

## Compatible Patch Versions

Use patch versions, such as `1.1.x`, for changes that do not affect scores:

- README or documentation edits.
- Report formatting changes.
- Non-scoring CLI ergonomics.
- Bug fixes that only improve error reporting.

## New Score Line

Use minor versions, such as `1.x.0`, when scores can change:

- Case prompt changes.
- Fixture changes.
- Checker changes.
- Partial scorer changes.
- Dimension or weight changes.
- Tool protocol changes.

## Major Redesign

Use `2.0.0` for methodology redesign:

- Different dimensions.
- Different number of cases.
- LLM judge integration.
- Non-local or online dependencies.
- A fundamentally different harness.
