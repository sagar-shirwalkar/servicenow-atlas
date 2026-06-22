---
name: atlas-build-bundle
description: >-
  Build the portable RAG bundle: clone docs, chunk, embed, package tarball.
  Use when the task involves building a bundle locally (`atlas-build`), smoke
  testing a bundle (`atlas-smoke`), or adding a new publication.
---

## When to use

- User asks to "build the bundle", "run atlas-build", "create a release bundle", "generate embeddings"
- User needs a local bundle for development (`--max-files 100`, `--publication it-service-management`)
- User asks to "add a new publication" to the repo and rebuild
- User is troubleshooting a failed CI bundle build

## Not for

- Deploying or releasing the bundle (use `atlas-ci-release`)
- Evaluating RAG quality (use `atlas-rag-evaluation`)

## Workflow

### 1. Pre-flight check

Always run `atlas-doctor` first to confirm the environment is ready:

```bash
uv run atlas-doctor
```

This checks:
- Git is installed and the docs repo is accessible
- Python version is >= 3.11
- Required packages (mcp, numpy, pyyaml, etc.) are installed
- HF model cache has the selected model (or can fetch it)
- Disk space is sufficient for the expected bundle size

Fix any failures before proceeding.

### 2. Choose your build mode

**Smoke build** (fast, for development — use first):
```bash
uv run atlas-build --limit 100
```

**Full local build** (all publications, MLX backend — use for production):
```bash
uv run atlas-build
```

**Single publication** (iterate on one docs section):
```bash
uv run atlas-build --publication it-service-management
```

**CI-matching build** (reproduce CI conditions — slow on 2 cores):
```bash
uv run atlas-build --model Xenova/bge-small-en-v1.5 --backend onnx-cpu
```

### 3. Verify the artifacts

After a successful build, the output is `<BUNDLE_DIR>/atlas-bundle.tar.zst`.

List contents without extracting:
```bash
tar --zstd -tf <BUNDLE_DIR>/atlas-bundle.tar.zst
```

Expected structure:
```
manifest.json
chunks/00000000.parquet
chunks/00000001.parquet
...
embeddings/00000000.parquet
embeddings/00000001.parquet
...
```

### 4. Run the smoke test

```bash
uv run atlas-smoke
```

This builds a 20-file bundle, fires a query, and returns exit code 0 on success. Run this before committing or considering any build successful.

## Common flags

| Flag | Purpose |
|---|---|
| `--model` | Override the HF model ID (default: `TransformersPseudoImpact/bge-base-en-v1.5`) |
| `--backend` | `mlx`, `onnx-cpu`, `onnx-gpu` (default: auto-detect) |
| `--limit` | File limit for smoke/development builds |
| `--publication` | Single publication folder |
| `--no-cache` | Force re-download of docs |
| `--bundle-dir` | Output directory (default: `data/bundles/<timestamp>`) |

## Adding a new publication

1. Add the publication folder to `data/servicenow-docs/` (git submodule update or fresh clone).
2. Rebuild the bundle — the chunker auto-discovers publications.
3. Update `manifest.json` will include the new publication.
4. If CI builds are triggered by tags, create a new tag.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `atlas-doctor` fails on "HF cache" | Model not downloaded | `uv run atlas-doctor --fix` or download manually |
| Build crashes during chunking | Corrupted docs clone | `git -C data/servicenow-docs stash && git -C data/servicenow-docs pull` |
| Build crashes during embedding | OOM | Reduce batch size or use `onnx-cpu` |
| Smoke test returns non-zero | Extraction/missing files | Check the temporary directory and manifest |
