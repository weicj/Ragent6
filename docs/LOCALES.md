# Prompt Sets

Ragent6 `0.2.0` supports two prompt sets under the same benchmark methodology.

| Locale | Manifest | Intended Use | Prompt Files |
| --- | --- | --- | --- |
| `en-US` | `manifests/ragent6_0_2_0_en_US.json` | English prompt set. | `*.en-US.txt` |
| `zh-CN` | `manifests/ragent6_0_2_0_zh_CN.json` | Chinese prompt set. | `*.zh-CN.txt` |

Both prompt sets share case IDs, fixtures, expected semantics, checkers, dimensions, and weights. The prompt set changes the model-facing prompt and native harness system instructions.

Score reports should state which prompt set was used.

The default `manifests/ragent6.json` points to the `en-US` line.
