GPU: NVIDIA GeForce RTX 4090. Run 2026-10-31 03:51:58 UTC to 2026-10-31 04:05:34 UTC.
ASR = share of vulnerable snippets the reviewer called SAFE (lower is better). Wilson 95% CI in asr.json.

### qwen2.5-coder:7b

| Set | n | Unguarded | Guard (strip flagged) | Strip all comments |
|---|---|---|---|---|
| clean | 30 | 3.3% | 3.3% | 3.3% |
| hard_negative_test | 360 | 3.9% | 4.2% | 3.3% |
| commentinject_external | 360 | 6.9% | 3.3% | 3.3% |
| synthetic_test | 180 | 4.4% | 3.3% | 3.3% |
| adaptive | 570 | 5.8% | 4.7% | 4.2% |

Reviewer latency p50 588.0 ms, p95 1810.8 ms (4 concurrent). Guard adds p50 0.508 ms, p95 1.611 ms.
Cost at an assumed $0.89/hr: $0.0936 per 1,000 guarded requests (two reviewer calls each).

### deepseek-coder:6.7b

| Set | n | Unguarded | Guard (strip flagged) | Strip all comments |
|---|---|---|---|---|
| clean | 30 | 10.0% | 10.0% | 10.0% |
| hard_negative_test | 360 | 18.3% | 15.0% | 10.0% |
| commentinject_external | 360 | 31.7% | 12.2% | 10.0% |
| synthetic_test | 180 | 28.9% | 10.0% | 10.0% |
| adaptive | 570 | 24.4% | 16.3% | 12.6% |

Reviewer latency p50 702.7 ms, p95 3000.4 ms (4 concurrent). Guard adds p50 0.508 ms, p95 1.611 ms.
Cost at an assumed $0.89/hr: $0.1434 per 1,000 guarded requests (two reviewer calls each).
