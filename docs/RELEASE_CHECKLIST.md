# Candidate Checklist

Use this checklist before publishing a Ragent6 score table or candidate leaderboard.

## Repository

- `manifests/ragent6.json` has the intended `suite_version`.
- `docs/CASES.md` matches the manifest case order.
- `README.md`, `METHODOLOGY.md`, and `docs/VERSIONING.md` describe the same scoring policy.
- Generated `results/`, generated `reports/`, model files, and local credentials are not committed.
- Raw model traces may be archived locally under `results/by-model/<model-slug>/<suite-version>/<run-id>/`; these run outputs are intentionally ignored by git.

## Validation

```bash
python3 -m compileall -q ragent6 scripts
python3 scripts/run_eval.py --manifest manifests/ragent6_0_2_0_en_US.json --adapter mock --out results/mock-0.2.0-en-US
python3 scripts/run_eval.py --manifest manifests/ragent6_0_2_0_zh_CN.json --adapter mock --out results/mock-0.2.0-zh-CN
python3 scripts/release_audit.py --manifest manifests/ragent6_0_2_0_en_US.json --suite-version 0.2.0 --locale en-US
python3 scripts/release_audit.py --manifest manifests/ragent6_0_2_0_zh_CN.json --suite-version 0.2.0 --locale zh-CN
python3 scripts/score_results.py --metadata examples/model_metadata.example.json
```

Expected mock result:

```text
Ragent6 0.2.0 en-US: 60/60 (invalid=0)
Ragent6 0.2.0 zh-CN: 60/60 (invalid=0)
```

## Score Tables

- Include only full 60-case runs with `invalid_cases == 0`.
- Keep `en-US` and `zh-CN` score tables separate.
- Disable hidden thinking/reasoning modes for comparable local model runs.
- Publish `partial_weighted` as the primary score and `strict_raw` as the auxiliary pass count.
- Do not mix scores from different score lines or different locales in one leaderboard.
