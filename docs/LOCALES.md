# Locale Score Lines

Ragent6 `0.2.0` supports two locale score lines under the same benchmark methodology.

| Locale | Manifest | Intended Use | Prompt Files |
| --- | --- | --- | --- |
| `en-US` | `manifests/ragent6_0_2_0_en_US.json` | International default benchmark line. | `*.en-US.txt` |
| `zh-CN` | `manifests/ragent6_0_2_0_zh_CN.json` | Chinese local Agent benchmark line. | `*.zh-CN.txt` |

Both locales share case IDs, fixtures, expected semantics, checkers, dimensions, and weights. The locale changes the model-facing prompt and native harness system instructions.

Scores are only comparable within the same locale. Do not mix `en-US` and `zh-CN` runs in one leaderboard.

The default `manifests/ragent6.json` points to the `en-US` line.
