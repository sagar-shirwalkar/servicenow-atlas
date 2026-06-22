---
name: atlas-rag-evaluation
description: >-
  Evaluate RAG quality: run Precision@10 and MRR against a bundle, interpret
  the scores, and compare CI-built vs locally-built bundles.
  Use when assessing bundle quality, comparing backends, or investigating a
  regressed search result.
---

## When to use

- User asks to "evaluate RAG quality", "run the evaluation script", "check search quality"
- User is comparing MLX vs ONNX+CPU embedding quality
- User wants to verify that a CI-built bundle meets the quality bar
- User suspects a regression in search relevance after a change

## Workflow

### 1. Select a bundle

List available bundles:
```bash
ls data/bundles/
```

Pick the one you want to evaluate.

### 2. Run the evaluation

```bash
# Point BUNDLE_DIR at the bundle and run
BUNDLE_DIR=data/bundles/<timestamp> uv run atlas-eval
```

If the eval script is already registered as a console script. Otherwise run directly:
```bash
BUNDLE_DIR=data/bundles/<timestamp> uv run python atlas/evaluate_rag.py
```

### 3. Read the results

The output looks like:

```
Query: "how to create an incident"
  P@10: 0.90    MRR: 1.0000
...
Mean P@10 over 10 queries: 0.89
Mean MRR over 10 queries:  0.94
```

**Precision@10 (P@10)**: Fraction of the top-10 results that are relevant. A score of 0.89 means ~9 of 10 returned chunks are on-topic.

**Mean Reciprocal Rank (MRR)**: How high the first relevant result appears. 1.0 means the top result is always relevant; 0.94 means the first relevant result is typically in position 1–2.

### 4. Benchmark bar

| Metric | Minimum | Target | Excellent |
|---|---|---|---|
| Precision@10 | 0.75 | 0.85 | 0.95+ |
| MRR | 0.80 | 0.90 | 0.97+ |

- A score below Minimum means the bundle is not usable — investigate chunk boundaries, model, or embeddings.
- Scores between Minimum and Target may be acceptable for development but should not ship to CI.
- Target or higher is required for a release build.

### 5. Compare CI vs local

To compare, build two bundles with the same model on CI and locally:

```bash
# Local (MLX)
uv run atlas-build --model Xenova/bge-small-en-v1.5
BUNDLE_DIR=data/bundles/<local> uv run atlas-eval

# Download CI bundle from GitHub Releases
gh release download <tag> --pattern '*.tar.zst'
tar --zstd -xf atlas-bundle-*.tar.zst -C /tmp/ci-bundle
BUNDLE_DIR=/tmp/ci-bundle uv run atlas-eval
```

Compare the mean scores. Small differences (<0.02) are expected due to float rounding.

## Interpretation

| Delta | Meaning |
|---|---|
| <0.01 | Negligible — bundles are equivalent |
| 0.01–0.03 | Minor — likely from int8 quantisation noise |
| 0.03–0.05 | Moderate — investigate chunk boundary differences |
| >0.05 | Significant — model or data divergence |

## References

- `README.md` §11 — Validate RAG quality
- `atlas/evaluate_rag.py` — The evaluation script
- MTEB leaderboard for model-specific expected scores
