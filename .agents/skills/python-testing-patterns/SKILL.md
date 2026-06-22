---
name: python-testing-patterns
description: >-
  Test conventions for the atlas project: pytest setup, fixture patterns,
  mocking external dependencies, and smoke test patterns.
  Use when writing new tests, setting up test infrastructure, or debugging a
  test failure.
---

## When to use

- Writing unit or integration tests for the project
- Setting up test infrastructure (conftest.py, fixtures)
- Adding tests for a new module
- Debugging a failing test

## Prerequisites

Tests require the dev dependencies:
```bash
uv sync --extra dev
```

## Test structure

Tests live in `tests/` at the project root, mirroring `atlas/`:

```
tests/
├── conftest.py          # Shared fixtures
├── test_chunk.py        # Tests for atlas/chunk.py
├── test_make_bundle.py  # Tests for atlas/make_bundle.py
└── test_embed/
    ├── conftest.py      # Embedder fixtures
    └── test_onnx.py     # Tests for atlas/embed/onnx.py
```

## Fixture patterns

Use `conftest.py` for shared fixtures. Keep them scoped appropriately.

### `tests/conftest.py`

```python
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
import tempfile

import pytest


@pytest.fixture
def tmp_bundle_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for bundle output."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
```

### Mocking external dependencies

For tests that should not hit Hugging Face or the network:

```python
@pytest.fixture(autouse=True)
def mock_hf_download(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent accidental network calls during tests."""

    def fake_download(*args, **kwargs) -> str:
        return "/tmp/fake-model-dir"

    monkeypatch.setattr(
        "huggingface_hub.snapshot_download",
        fake_download,
    )
```

For tests that need real ONNX inference, mark them as integration:

```python
@pytest.mark.integration
def test_onnx_embedder_inference(onnx_embedder: OnnxEmbedder) -> None:
    embeddings = onnx_embedder.embed(["hello world"])
    assert embeddings.shape[1] == onnx_embedder.dim
```

## Test patterns by module

### `atlas/chunk.py`

- Unit test `parse_frontmatter` with: valid YAML, malformed YAML, no frontmatter, empty file.
- Unit test `_split_on_h2` with: normal headings, no headings, consecutive headings, heading at EOF.
- Integration test `chunk_file` against a real markdown file in `tests/fixtures/`.

### `atlas/make_bundle.py`

- Test `write_manifest` with and without `embedding_dim`.
- Test `write_chunks` with sample chunk data.
- Integration test: build a bundle from `tests/fixtures/` docs and verify outputs.

### `atlas/embed/`

- Test `Embedder` base class contract (ABC).
- Test `OnnxEmbedder` model resolution: `snapshot_download` path.
- Test `dim` property from ONNX model shape.
- Test `MlxEmbedder` zero-vector fallback.
- Mark GPU tests as `@pytest.mark.gpu` (skipped when no GPU).

## Coverage

- Target: 80%+ for utility modules (`chunk.py`, `make_bundle.py`).
- Core embedding paths: integration tests only (too costly to unit-test inference).
- Smoke test (`atlas-smoke`): always runs end-to-end, never mocked — this is the CI gate.

## Running tests

```bash
# All non-integration tests (fast)
uv run pytest -m "not integration and not gpu"

# Integration tests (requires model download)
uv run pytest -m integration

# Full suite
uv run pytest
```

## References

- `atlas/smoke_test.py` — the end-to-end smoke test pattern
- `README.md` §7 — testing roadmap
- `pyproject.toml` — dev dependency (`pytest>=8.0`)
