# AGENTS.md - Ragent6

This repository is the clean, publishable Ragent6 benchmark candidate line.

- Current release versions: `en-US` is `0.2.0`; `zh-CN` is `0.2.2`.
- `0.2.0` is the first public Ragent6 benchmark release.
- `0.2.2` is the Chinese prompt-set and native-harness adaptation release; it keeps the same case IDs, fixtures, dimensions, and weights as `0.2.0`, but updates Chinese prompts, tool-harness guidance, and checker equivalence rules.
- Default manifest: `manifests/ragent6.json` (`en-US`). Current Chinese locale manifest: `manifests/ragent6_0_2_2_zh_CN.json`.
- Primary score is deterministic partial score, weighted to 100.
- Strict `0/1` pass count is an auxiliary `x/60` field.
- Hidden reasoning must be disabled for comparable local model runs.
- If any case, checker, partial scorer, dimension, prompt set, or weight changes in a way that can affect scores, bump the benchmark version.
- Keep generated results and model files out of git.
