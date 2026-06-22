---
name: python-type-safety
description: >-
  Enforce consistent type hint usage across the atlas project. Covers
  annotation style, `from __future__ import annotations`, Literal and Protocol
  patterns, TYPE_CHECKING for optional dependencies, and recommended type
  checker config.
  Use when writing or reviewing type annotations.
---

## When to use

- Annotating new Python code
- Reviewing PRs for type correctness
- Setting up a type checker (mypy or pyright) for the project
- Debugging a type-related issue

## Project conventions

### `from __future__ import annotations`

**Required in every `.py` file** (after the module docstring):

```python
"""Module docstring."""

from __future__ import annotations
```

This defers all annotation evaluation to strings, which:
- Eliminates runtime import overhead for annotations
- Allows forward references without quotes
- Works naturally with `requires-python = ">=3.11"`

### Parameter and return type annotations

Every function must have annotated parameters and return type.

```python
def parse_frontmatter(text: str) -> tuple[dict, str]: ...
def embed(self, texts: list[str]) -> np.ndarray: ...
def chunk_file(path: Path, repo_root: Path) -> list[dict]: ...
```

Use built-in generic types (`list[str]`, `dict[str, Any]`, `tuple[str, str]`) — these are available in Python 3.9+ and compatible with the `from __future__ import annotations` approach.

### `Literal` for constrained values

Use `Literal` when a parameter accepts only a fixed set of string values:

```python
from typing import Literal

Backend = Literal["mlx", "onnx-cpu", "onnx-gpu", "auto"]
```

This enables the type checker to validate callers and provides autocomplete in IDEs.

### `TYPE_CHECKING` for optional dependencies

When a module imports a heavy or optional dependency only for type-checking, gate it behind `TYPE_CHECKING` and provide a runtime fallback:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import mlx.core as mx


def _import_mlx() -> None:
    try:
        import mlx.core as mx
    except ImportError:
        raise ImportError(
            "MLX backend requires 'mlx' package. "
            "Install with: uv sync --extra mlx"
        )
```

This pattern is used in `atlas/embed/mlx.py` for the MLX backend.

### Abstract base classes with `abc.ABC`

Use `abc.ABC` and `@abstractmethod` for defining interfaces:

```python
from abc import ABC, abstractmethod


class Embedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray: ...
```

### What to avoid

| Don't use | Why | Instead |
|---|---|---|
| `typing.List`, `typing.Dict` | Deprecated in Python 3.9 | `list`, `dict` |
| `typing.Optional` | Redundant with `Union[X, None]` syntax | `X \| None` (Python 3.10+) |
| Unannotated `self` / `cls` | Unnecessary — type checkers infer these | Omit |
| `Any` where a concrete type exists | Loses all type safety | Narrow to the actual type |

### `Any` usage

`Any` is reserved for genuinely dynamic types:
- JSON payloads with unknown structure
- `**kwargs` that forward to third-party libraries
- Generic dict values where the value type varies

```python
def handler(arguments: dict[str, Any]) -> str: ...
```

## Recommended type checker setup

The project has **no type checker configured** (no mypy.ini, no pyrightconfig.json). Recommended:

### mypy

Create `pyproject.toml` section or `mypy.ini`:

```toml
[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

### pyright

Create `pyrightconfig.json`:

```json
{
  "include": ["atlas"],
  "pythonVersion": "3.11",
  "typeCheckingMode": "strict"
}
```

## CI integration

Once a type checker is configured, add a step to `build-bundle.yml`:

```yaml
- name: Type check
  run: uv run mypy atlas/
```

Run this before the build step so type errors fail fast.

## References

- `atlas/embed/base.py` — ABC + Literal pattern
- `atlas/embed/mlx.py` — TYPE_CHECKING pattern
- `atlas/embed/onnx.py` — parameter annotations with `snapshot_download`
- `atlas/chunk.py` — return type annotations with complex types
