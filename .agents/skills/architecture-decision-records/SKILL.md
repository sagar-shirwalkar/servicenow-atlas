---
name: architecture-decision-records
description: >-
  Write and maintain Architecture Decision Records (ADRs) for the atlas
  project. Covers ADR format, where to store them, when to create one, and
  examples based on past decisions.
  Use when making a significant technical decision that should be recorded for
  future maintainers.
---

## When to use

Create an ADR when you make a decision that is:
- **Significant** — affects multiple modules, backends, or the build process
- **Non-obvious** — the rationale won't be immediately clear to future readers
- **Costly to reverse** — changing it later would require substantial rework
- **Architecturally binding** — constrains future design choices

Examples from this project's history that should have been ADRs:
- Choosing MLX over CoreML for Apple Silicon
- Using `snapshot_download` instead of `cached_file` for ONNX tokenizer loading
- Reducing CI model from BGE-base (768-dim) to BGE-small (384-dim) for timeout reasons
- Choosing int8 quantisation over FP32 for CPU builds

Do NOT create ADRs for:
- Bug fixes
- Routine dependency upgrades
- Cosmetic refactors
- Decisions documented entirely by code comments

## ADR format

Each ADR is a markdown file at `docs/adr/NNNN-title-with-dashes.md`.

### File name

```
NNNN-title-with-dashes.md
```

Where `NNNN` is the next available number, zero-padded to 4 digits.

### Frontmatter

```yaml
---
date: 2026-06-22
status: accepted  # proposed | accepted | deprecated | superseded
supersedes:  # optional: ADR number this replaces
superseded_by:  # optional: ADR number that replaces this
---
```

### Template

```markdown
---
date: <YYYY-MM-DD>
status: <proposed|accepted|deprecated|superseded>
---

# <Number>. <Title>

## Context

What is the problem we are solving? What constraints or forces are at play?
Include relevant background, requirements, and trade-offs.

## Decision

What did we decide? State it clearly and concretely.

## Rationale

Why this option over the alternatives? List 2–3 options considered and why
each was or wasn't chosen.

## Consequences

What becomes easier or harder as a result of this decision?
What does this decision enable or foreclose?

## Compliance

How will future code or CI enforce this decision? (optional)
```

## Where to store

```
docs/adr/
├── index.md       # Table of contents, generated
├── 0001-mlx-over-coreml.md
└── 0002-snapshot-download-for-tokenizer.md
```

## ADR lifecycle

1. **Proposed** — Decision is being discussed. File with `status: proposed`.
2. **Accepted** — Decision is final. Change status to `accepted`.
3. **Deprecated** — Decision is no longer relevant but not yet superseded.
4. **Superseded** — A newer ADR replaces this one. Set `superseded_by`.

## Examples

### 0001: Choose MLX over CoreML for Apple Silicon

**Decision**: Use MLX framework for Apple Silicon GPU acceleration instead of CoreML.

**Rationale**: CoreML's ONNX conversion flow (`coremltools`) was unstable — caused SIGKILL crashes during conversion and produced models 30–40× slower than CPU. MLX provides direct model loading, stable Apple Silicon acceleration, and native float16 support.

**Consequences**: MLX becomes the default backend on Apple Silicon. ONNX+CPU remains the CI fallback. Linux/Windows users get ONNX+CPU only.

### 0002: Use snapshot_download for ONNX tokenizer loading

**Decision**: Use `huggingface_hub.snapshot_download` instead of `transformers.cached_file` to resolve the model directory.

**Rationale**: `cached_file` downloads only the ONNX file, missing tokenizer.json, config.json, and vocab files. `snapshot_download` guarantees the full model snapshot lands in one directory, so tokenizer loading never fails with "file not found."

**Consequences**: Slightly larger initial download (all model files instead of just ONNX). `snapshot_download` respects `HF_TOKEN` environment variable.

## References

- `README.md` — contains informal design rationale that could be migrated to ADRs over time
- Module-level docstrings in `atlas/embed/onnx.py`, `atlas/chunk.py`, `atlas/rag_server.py` — embedded design decisions
