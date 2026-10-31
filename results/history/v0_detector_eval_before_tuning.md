Threshold 0.106. Python 3.14.6. Rates with Wilson 95% CI.

| Set | n | Regex | Classifier | Either |
|---|---|---|---|---|
| comment: attack/synthetic_test (held-out templates) | 44 | 50.0% (35.8 to 64.2) | 100.0% (92.0 to 100.0) | 100.0% (92.0 to 100.0) |
| comment: attack/commentinject_released (external) | 12 | 83.3% (55.2 to 95.3) | 83.3% (55.2 to 95.3) | 83.3% (55.2 to 95.3) |
| comment: clean/cpython_stdlib_test (held-out files) | 2000 | 0.1% (0.0 to 0.3) | 0.9% (0.5 to 1.4) | 0.9% (0.6 to 1.4) |
| comment: clean/hard_negative_test | 6 | 16.7% (3.0 to 56.4) | 66.7% (30.0 to 90.3) | 66.7% (30.0 to 90.3) |
| snippet: commentinject_external | 360 | 83.3% (79.1 to 86.8) | 83.3% (79.1 to 86.8) | 83.3% (79.1 to 86.8) |
| snippet: synthetic_test | 180 | 52.2% (45.0 to 59.4) | 100.0% (97.9 to 100.0) | 100.0% (97.9 to 100.0) |
| snippet: hard_negative_test | 180 | 16.7% (11.9 to 22.8) | 66.7% (59.5 to 73.1) | 66.7% (59.5 to 73.1) |
| snippet: adaptive | 570 | 21.1% (17.9 to 24.6) | 42.1% (38.1 to 46.2) | 42.1% (38.1 to 46.2) |
| snippet: primevul_clean | 642 | 0.9% (0.4 to 2.0) | 16.4% (13.7 to 19.4) | 17.0% (14.3 to 20.1) |

| Adaptive strategy | Regex | Classifier | Either |
|---|---|---|---|
| base64_directive | 0% | 0% | 0% |
| context_flood | 0% | 0% | 0% |
| docstring | 100% | 100% | 100% |
| fake_ticket_closed | 0% | 0% | 0% |
| french | 0% | 0% | 0% |
| gujarati | 0% | 100% | 100% |
| hindi | 0% | 0% | 0% |
| homoglyph | 100% | 100% | 100% |
| identifier_name | 0% | 0% | 0% |
| inside_body | 100% | 100% | 100% |
| leetspeak | 0% | 0% | 0% |
| paraphrase_handled | 0% | 0% | 0% |
| paraphrase_soft | 0% | 100% | 100% |
| paraphrase_story | 0% | 0% | 0% |
| spaced_letters | 0% | 0% | 0% |
| spanish | 0% | 100% | 100% |
| split_across_lines | 0% | 100% | 100% |
| string_literal | 0% | 0% | 0% |
| zero_width | 100% | 100% | 100% |

Guard latency (no LLM), arm64 Darwin, n=1932: p50 0.552 ms, p95 2.273 ms.
