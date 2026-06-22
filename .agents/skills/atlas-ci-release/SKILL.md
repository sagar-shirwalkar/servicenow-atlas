---
name: atlas-ci-release
description: >-
  Manage CI bundle releases: manual dispatch, tag naming, monitoring the
  build-bundle workflow, promoting a release, and rolling back.
  Use when releasing a new bundle, debugging a CI failure, or rolling back to a
  previous bundle.
---

## When to use

- User asks to "release a new bundle", "trigger a CI build", "create a release"
- User wants to "tag a release", "cut a release"
- A CI build failed and needs investigation
- User wants to "roll back to the previous bundle"

## Not for

- Building the bundle locally (use `atlas-build-bundle`)
- Changing the CI workflow itself (edit `.github/workflows/build-bundle.yml` manually)

## Workflow

### 1. Manual dispatch

Go to GitHub → Actions → Build Bundle → Run workflow.

Parameters:
| Parameter | Value | When |
|---|---|---|
| `model_id` | `Xenova/bge-small-en-v1.5` | Default — production builds |
| `ref` | `main` | Stable releases |
| `ref` | `<branch>` | Testing a feature branch |

Do NOT dispatch from `main` if there are unmerged changes that affect the bundle content.

### 2. Tag naming convention

Tags are auto-generated from the workflow run: `bundle-<YYYYMMDD>-<run_number>` (e.g., `bundle-20260622-42`).

For manual tags (when the auto-tag is insufficient):
```bash
git tag bundle-<YYYYMMDD>-<run_number>-<reason>
git push origin bundle-<YYYYMMDD>-<run_number>-<reason>
```

Reasons: `hotfix`, `rollback`, `rc1`, `rc2`.

### 3. Monitor the workflow

The workflow takes ~30–60 minutes.

| Phase | Duration | Key log lines |
|---|---|---|
| Setup | 1 min | `Setup uv`, `Cache npm` |
| Clone docs | 2–3 min | `Cloning servicenow-docs` |
| Chunk | 2–5 min | `Chunked N files` |
| Download model | 1–3 min | `Downloading Xenova/bge-small-en-v1.5` |
| Embed | 15–30 min | `Embedding chunk N/M` |
| Package | 1 min | `Creating tarball` |
| Smoke test | 2 min | `Smoke test passed` |
| Publish | 1 min | `Uploading release asset` |

If the workflow exceeds 60 minutes, check the runner logs for:
- Slow model download (HF mirror issues)
- OOM (runner has 2 vCPUs / 7 GB)
- Stuck chunking (infinite loop in a single file)

### 4. Promote a release

When the build workflow succeeds:

1. The tarball is uploaded as a GitHub Release asset.
2. The release name matches the tag.
3. To make it the "latest" release:
   ```bash
   gh release edit <tag> --latest
   ```

### 5. Roll back

To revert to a previous bundle:

```bash
# Find the previous release's tag
gh release list --limit 10

# Download the previous bundle
gh release download <previous-tag> --pattern '*.tar.zst'

# Make it the latest
gh release edit <previous-tag> --latest
```

No code rollback is needed — bundles are independent artifacts. Just re-point consumers.

## CI workflow reference

File: `.github/workflows/build-bundle.yml`

| Key detail | Value |
|---|---|
| Trigger | Monthly cron (`0 6 1 * *`) + `workflow_dispatch` |
| Runner | `ubuntu-latest` (2 vCPU, 7 GB, no GPU) |
| Model | `Xenova/bge-small-en-v1.5` (int8, 384-dim) |
| Backend | ONNX+CPU (forced via `--backend onnx-cpu`) |
| Batch size | 256 |
| Env | `HF_TOKEN` set from secrets |
| Post-build | `atlas-smoke` |
| Artifact | GitHub Release (auto-tag) |
