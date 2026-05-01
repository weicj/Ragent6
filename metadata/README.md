# Metadata

`score_results.py` expects a metadata JSON file with this shape. The example
below points at the mock smoke output so the scoring command works after
running `make mock`.

```json
{
  "models": [
    {
      "name": "Mock Golden Trace",
      "result_dir": "results/mock-1.1.0",
      "audit_group": "ragent6-1.1.0-smoke",
      "family": "mock",
      "generation": "golden",
      "generation_rank": 1,
      "arch": "dense",
      "original": true,
      "size_rank": 0,
      "precision_group": "mock",
      "precision_rank": 0
    }
  ]
}
```

The audit fields are optional for simple scoring, but recommended for consistency checks.

For local model archives, prefer storing raw runs under:

```text
results/by-model/<model-slug>/<suite-version>/<run-id>/
```

`result_dir` may point to either the flat mock path shown above or the nested
per-model path, for example:

```json
{
  "name": "Example Local Model",
  "result_dir": "results/by-model/example-local-model/1.1.0/run-001"
}
```
