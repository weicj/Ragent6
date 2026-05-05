# Prompt Sets

Ragent6 supports English and Chinese prompt sets under the same benchmark methodology.

| Locale | Manifest | Intended Use | Prompt Files |
| --- | --- | --- | --- |
| `en-US` | `manifests/ragent6_0_2_0_en_US.json` | English `0.2.0` prompt set. | `*.en-US.txt` |
| `zh-CN` | `manifests/ragent6_0_2_1_zh_CN.json` | Cleaned Chinese `0.2.1` prompt set. | `*.zh-CN.txt` |

Both prompt sets share case IDs, fixtures, expected semantics, checkers, dimensions, and weights. The prompt set changes the model-facing prompt and native harness system instructions.

Score reports should state the benchmark version and prompt set used. Do not mix `en-US 0.2.0`, historical `zh-CN 0.2.0`, and current `zh-CN 0.2.1` results in one leaderboard.

The default `manifests/ragent6.json` points to the `en-US` line.
