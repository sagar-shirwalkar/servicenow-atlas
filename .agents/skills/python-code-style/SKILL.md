---
name: python-code-style
description: >-
  Enforce consistent Python code style across the project. Covers import
  ordering, string quoting, naming conventions, docstring format, and
  recommended linter setup. Use when writing new code, reviewing PRs for style,
  or configuring a linter.
---

## When to use

- Writing new Python files for the project
- Reviewing code for style consistency
- Configuring ruff or another linter/formatter
- Onboarding a new contributor

## Project conventions

These are the conventions established by the existing codebase at `atlas/`.

### Import ordering

Three groups separated by a blank line:

```python
import re
from pathlib import Path

import numpy as np
import yaml

from .base import Embedder
```

| Group | Contents |
|---|---|
| 1 — Standard library | `os`, `re`, `pathlib`, `argparse`, `json`, etc. |
| 2 — Third-party | `numpy`, `yaml`, `mcp`, `onnxruntime`, `transformers`, etc. |
| 3 — Local (relative) | `from .base import ...`, `from .chunk import ...` |

Within each group, sort alphabetically. Use `import module` over `from module import symbol` unless you need fewer than 3 symbols from a module.

### String quoting

**Double quotes** for all strings and docstrings:

```python
name = "servicenow-atlas"
description = f"Bundle version {version}"
```

Single quotes are allowed only to avoid escaping inside f-strings:
```python
f"    - {h['publication']}/{h['file']}"
```

### Naming conventions

| Category | Style | Example |
|---|---|---|
| Modules/packages | `snake_case` | `chunk.py`, `make_bundle.py` |
| Classes | `PascalCase` | `OnnxEmbedder`, `MlxEmbedder` |
| Functions/methods | `snake_case` | `parse_frontmatter`, `embed_with_progress` |
| Constants | `UPPER_CASE` | `DEFAULT_MODEL_ID`, `_MAX_CHUNK_CHARS` |
| Private (`_` prefix) | `_single_leading` | `_resolve_model_dir`, `_FRONTMATTER_RE` |
| Type variables | `_T` or descriptive | — |

### Docstrings

Triple double quotes (`"""..."""`). Module-level docstrings provide design context. Function docstrings describe parameters, return values, and edge cases.

For RST cross-references to other code, use `:meth:`, `:class:`, `:mod:`:
```python
"""...as described in :meth:`Embedder.embed`..."""
```

When documenting parameters inline (not via Google-style section headers), place the description after `--`:
```python
def chunk_file(path: Path, repo_root: Path) -> list[dict]:
    """Chunk a single markdown file, splitting on H2 boundaries.

    Malformed YAML frontmatter is logged and treated as no frontmatter.
    """
```

### f-strings

Always use f-strings. Do not use `.format()` or `%` formatting.

```python
# Correct
logger.info("Chunked %s files in %.2fs", count, elapsed)

# Also correct (f-strings for display strings)
path = f"{publication}/{filename}"
```

### Line length

No strict line length is enforced. Use judgment:
- Keep lines under ~100 characters when readable.
- Break long strings at logical boundaries (e.g., between sentences).
- Long argument lists can span multiple lines.

### Blank lines

- Two blank lines before top-level class/function definitions.
- One blank line between methods inside a class.
- One blank line after module docstring.
- Import groups separated by one blank line.

### `from __future__ import annotations`

Add this as the first import in every `.py` file (after the module docstring):

```python
"""Module docstring."""

from __future__ import annotations
```

This defers annotation evaluation and is required by the `requires-python = ">=3.11"` constraint.

## Recommended setup

### Configure ruff (not currently set up — recommended)

Create `.ruff.toml`:

```toml
target-version = "py311"
line-length = 100

[lint]
select = ["E", "F", "I", "N", "W", "UP", "D"]
ignore = ["D203", "D213", "D415"]  # Allow flexible docstring convention

[format]
quote-style = "double"
```

Then run:
```bash
ruff check .
ruff format .
```

### Pre-commit hook (optional)

If you set up pre-commit, add `.pre-commit-config.yaml` with `ruff` and `ruff-format`.

## References

- `pyproject.toml` — project configuration
- `README.md` — not a style guide, but documents project conventions
- `ruff` documentation for rule selection
