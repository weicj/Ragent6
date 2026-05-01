# AGENTS.md - Ragent6

This repository is the clean, publishable Ragent6 benchmark candidate line.

- Current release version: `0.2.0`.
- Ragent6 has two locale score lines under the same methodology: `en-US` for international users and `zh-CN` for Chinese users. Do not mix locale results in one leaderboard.
- There is no stable `1.x` release yet; earlier `1.0.0` and `1.1.0` outputs are historical calibration score lines only.
- Default manifest: `manifests/ragent6.json` (`en-US`). Chinese locale manifest: `manifests/ragent6_0_2_0_zh_CN.json`.
- Do not reintroduce historical experiment manifests or abandoned suite names into this repository.
- Primary score is deterministic partial score, weighted to 100.
- Strict `0/1` pass count is an auxiliary `x/60` field.
- Hidden reasoning must be disabled for comparable local model runs.
- If any case, checker, partial scorer, dimension, locale prompt, or weight changes in a way that can affect scores, bump the score-line version.
- Keep generated results and model files out of git.
