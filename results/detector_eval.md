Threshold 0.084. Python 3.14.6. Rates with Wilson 95% CI.

| Set | n | Regex | Classifier | Either |
|---|---|---|---|---|
| comment: attack/synthetic_test (held-out templates) | 44 | 50.0% (35.8 to 64.2) | 100.0% (92.0 to 100.0) | 100.0% (92.0 to 100.0) |
| comment: attack/commentinject_released (external) | 12 | 83.3% (55.2 to 95.3) | 83.3% (55.2 to 95.3) | 83.3% (55.2 to 95.3) |
| comment: clean/cpython_stdlib_test (held-out files) | 2172 | 0.1% (0.0 to 0.3) | 1.0% (0.6 to 1.5) | 1.0% (0.7 to 1.5) |
| comment: clean/cpython_headers_test (held-out files) | 328 | 0.0% (0.0 to 1.2) | 0.3% (0.1 to 1.7) | 0.3% (0.1 to 1.7) |
| comment: clean/hard_negative_test | 12 | 8.3% (1.5 to 35.4) | 58.3% (31.9 to 80.7) | 58.3% (31.9 to 80.7) |
| snippet: commentinject_external | 360 | 83.3% (79.1 to 86.8) | 83.3% (79.1 to 86.8) | 83.3% (79.1 to 86.8) |
| snippet: synthetic_test | 180 | 51.1% (43.9 to 58.3) | 100.0% (97.9 to 100.0) | 100.0% (97.9 to 100.0) |
| snippet: hard_negative_test | 360 | 8.3% (5.9 to 11.7) | 58.3% (53.2 to 63.3) | 58.3% (53.2 to 63.3) |
| snippet: adaptive | 570 | 21.1% (17.9 to 24.6) | 42.1% (38.1 to 46.2) | 42.1% (38.1 to 46.2) |
| snippet: primevul_clean_test | 442 | 0.9% (0.4 to 2.3) | 17.6% (14.4 to 21.5) | 18.6% (15.2 to 22.4) |

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

Guard latency (no LLM), arm64 Darwin, n=1912: p50 0.508 ms, p95 1.611 ms.
