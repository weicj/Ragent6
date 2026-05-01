# Model Result Archive

Use this directory for local per-model Ragent6 run outputs.

Recommended layout:

```text
results/by-model/<model-slug>/<suite-version>/<locale>/<run-id>/
```

Example:

```text
results/by-model/qwen3.6-27b-q4_k_m/0.2.0/en-US/2026-05-01-native-local/
```

Each run directory should be the direct output of `scripts/run_eval.py` and must contain:

- `summary.json`
- `summary.partial.json`
- `cases/<case_id>/trace.json`
- `cases/<case_id>/case_result.json`

These files are intentionally ignored by git because traces can be large and machine-specific. Commit only curated metadata, reports, or leaderboard artifacts that are safe to publish.

Suggested model slug format:

- Lowercase.
- Include base model, parameter size, and quantization when relevant.
- Use `-` or `_` consistently.
- Avoid spaces and shell-special characters.

Example run:

```bash
python3 scripts/run_eval.py \
  --manifest manifests/ragent6_0_2_0_en_US.json \
  --adapter native_local \
  --out results/by-model/qwen3.6-27b-q4_k_m/0.2.0/en-US/2026-05-01-native-local
```

`scripts/release_audit.py` and `scripts/build_leaderboard.py` scan `results/` recursively, so this nested layout is supported.
