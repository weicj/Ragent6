# AGENTS.md - Ragent6

This repository is the clean, publishable Ragent6 benchmark line.

- Current stable version: `1.1.0`.
- Default manifest: `manifests/ragent6.json`.
- Do not reintroduce historical experiment manifests or abandoned suite names into this repository.
- Primary score is deterministic partial score, weighted to 100.
- Strict `0/1` pass count is an auxiliary `x/60` field.
- Hidden reasoning must be disabled for comparable local model runs.
- If any case, checker, partial scorer, dimension, or weight changes in a way that can affect scores, bump the minor version at minimum.
- Keep generated results and model files out of git.
