# Prompt Sets

Ragent6 supports English and Chinese prompt sets under the same benchmark methodology.

| Locale | Manifest | Intended Use | Prompt Files |
| --- | --- | --- | --- |
| `en-US` | `manifests/ragent6_0_2_0_en_US.json` | English `0.2.0` prompt set. | `*.en-US.txt` |
| `zh-CN` | `manifests/ragent6_0_2_2_zh_CN.json` | Chinese `0.2.2` prompt, harness, and checker-equivalence adaptation line. | `*.zh-CN.txt` |

Both prompt sets share case IDs, fixtures, dimensions, and weights. The Chinese line changes the model-facing prompt, native harness system instructions, and deterministic equivalence rules needed for Chinese answers.

Score reports should state the benchmark version and prompt set used. Do not mix `en-US 0.2.0`, historical `zh-CN 0.2.0/0.2.1`, and current `zh-CN 0.2.2` results in one leaderboard.

The default `manifests/ragent6.json` points to the `en-US` line.
