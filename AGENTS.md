# AGENTS.md - Ragent6

This repository is the clean, publishable Ragent6 benchmark candidate line.

- Current release version: `0.2.0`.
- `0.2.0` is the first public Ragent6 benchmark release.
- Ragent6 provides `en-US` and `zh-CN` prompt sets under the same methodology.
- Default manifest: `manifests/ragent6.json` (`en-US`). Chinese locale manifest: `manifests/ragent6_0_2_0_zh_CN.json`.
- Primary score is deterministic partial score, weighted to 100.
- Strict `0/1` pass count is an auxiliary `x/60` field.
- Hidden reasoning must be disabled for comparable local model runs.
- If any case, checker, partial scorer, dimension, prompt set, or weight changes in a way that can affect scores, bump the benchmark version.
- Keep generated results and model files out of git.
