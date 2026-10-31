# Architecture

```mermaid
flowchart LR
    C[Client: CI job or PR bot] -->|POST /v1/scan + X-API-Key| A[FastAPI]
    A --> K{key valid?\nrate limit ok?\nsize ok?}
    K -- no --> E[401 / 429 / 413]
    K -- yes --> X[Extract comment blocks\nPython tokenize + ast\nC-like state machine]
    X --> N[Normalize\nNFKC, zero-width, homoglyphs]
    N --> R[Regex rules]
    N --> M[TF-IDF + logistic regression\nthreshold from val + dev]
    R --> D{flag block?}
    M --> D
    D --> S[Strip flagged blocks\nor all blocks]
    S --> V{review requested?}
    V -- no --> O[JSON: flags, guarded_code, latency]
    V -- yes --> B{spend cap\nreservation ok?}
    B -- no --> P[402]
    B -- yes --> L1[Reviewer on raw code]
    B -- yes --> L2[Reviewer on guarded code]
    L1 --> O
    L2 --> O
    A -.-> G[(JSON log line:\nkey hash, sizes, counts,\ncost, latency. No code.)]
```

## Pieces

| File | Job |
|---|---|
| `guard/comments.py` | Find comment blocks and remove them without touching code lines. Trailing comments are cut at the column. |
| `guard/rules.py` | Normalization and the regex baseline (8 rule groups). |
| `guard/classifier.py` | Train, pick the threshold, score. Comments under 3 words go to regex only. |
| `guard/core.py` | `Guard.scan`: combine detectors, build the guarded copy. |
| `guard/reviewer.py` | Mock, Ollama and Claude reviewers. Same prompt and verdict parser as CommentInject. |
| `guard/limits.py` | API keys, rate limit, monthly spend cap. |
| `guard/app.py` | HTTP layer and logging. |

## Known limits

- The rate limiter and spend file are per instance. Scaling past one machine needs a shared store (Redis, Postgres) for both.
- A multi-line block comment that starts after code on the same line is removed with its lines, including that code. Rare in practice; listed so nobody is surprised.
- Language detection is a heuristic. Pass `language` when you know it.
- The classifier is English-centric and was trained on one author's attack templates. The adaptive table in the README is the honest picture of what that misses.
