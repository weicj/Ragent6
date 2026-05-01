# Contributing

Ragent6 changes should preserve reproducibility and local determinism.

## Case Changes

- Keep case IDs stable within a published minor version.
- Add or change cases only in a new minor version.
- Every case must include `case.json`, `prompt.txt`, and a passing `mock_trace.json`.
- Prefer behavior-driven checkers over brittle exact-string checks unless the task explicitly tests exact formatting.

## Scoring Changes

- Any checker, partial scorer, dimension, or weight change that can affect model scores requires a minor version bump.
- Do not optimize cases solely to satisfy an expected model ordering. Audit checks are diagnostic, not the target.
- Keep scoring deterministic; do not add an LLM judge to the core benchmark.

## Validation

Run before submitting changes:

```bash
make test
```
