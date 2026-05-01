# Release Checklist

Use this checklist before publishing a Ragent6 release or leaderboard.

## Repository

- `manifests/ragent6.json` has the intended `suite_version`.
- `docs/CASES.md` matches the manifest case order.
- `README.md`, `METHODOLOGY.md`, and `docs/VERSIONING.md` describe the same scoring policy.
- Generated `results/`, generated `reports/`, model files, and local credentials are not committed.

## Validation

```bash
python3 -m compileall -q ragent6 scripts
python3 scripts/run_eval.py --manifest manifests/ragent6.json --adapter mock --out results/mock-1.0.0
python3 scripts/release_audit.py --manifest manifests/ragent6.json --suite-version 1.0.0
python3 scripts/score_results.py --metadata examples/model_metadata.example.json
```

Expected mock result:

```text
Ragent6 1.0.0: 60/60 (invalid=0)
```

## Score Tables

- Include only full 60-case runs with `invalid_cases == 0`.
- Disable hidden thinking/reasoning modes for comparable local model runs.
- Publish `partial_weighted` as the primary score and `strict_raw` as the auxiliary pass count.
- Do not mix scores from different minor versions in one leaderboard without explicit labels.
