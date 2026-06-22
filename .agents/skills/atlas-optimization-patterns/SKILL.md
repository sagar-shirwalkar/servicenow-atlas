---
name: atlas-optimization-patterns
description: >-
  Aggressive optimization patterns for atlas. Overrides standard Python
  defaults with zero-dep, startup-time, and memory-efficient alternatives.
  Honed for a project that runs a read-only parquet-backed RAG bundle
  loaded into numpy at startup and queried via MCP. Use when making any
  code change — these patterns take precedence over generic Python best
  practices.
---

## When to use

- Adding a new dependency — always ask "can I do this with numpy/pyarrow?"
- Choosing a data structure for the chunks table
- Writing startup/import-heavy code
- Adding CPU-bound parallel work
- Any change to `atlas/` source files

## Principles

1. **Zero new deps.** Every library adds import time, CVE surface, and
   lockfile bloat. Prefer numpy + pyarrow (already installed) over
   anything new. Pandas is explicitly banned — see patterns below.

2. **Optimize startup, not just hot path.** A ~300 ms pandas import
   on every `atlas-*` command hurts more than a 10 ms saving in a
   rarely-hit code path.

3. **DataFrame abstractions are overhead.** The chunks table is
   read-only, loaded once, and accessed by column. Store columns as
   `numpy arrays` for masks and `list[str]` for string data. Index
   by position, not by label.

4. **C-level string ops when possible.** Use `pyarrow.compute`
   (`match_substring`) instead of Python loops over 250k strings.
   Use `pc.match_substring(arrow_array, token)` — it's the
   same speed as pandas `str.contains`.

5. **Process-level parallelism for CPU-bound ONNX.** ONNX session.run
   is CPU-bound. Use `concurrent.futures.ProcessPoolExecutor` with
   `min(os.cpu_count(), 4)` workers, each loading its own ONNX session.
   Only for `onnx-cpu` backend — MLX and CUDA are sequential.

6. **Lazy init for argparse and other I/O.** Never call `parse_args()`
   or `read_parquet()` at module level. Use the `_get_args()` /
   `_bundle_cache` double-checked locking pattern from `rag_server.py`.

7. **Pre-compute at build time.** Norms, manifest SHAs, anything that
   can be computed once and stored. Query time should be as close to
   a single matrix multiply as possible.

8. **Single matrix multiply for cosine similarity.** 250k × 768 dims:
   `(embeddings @ query).flatten() / norms`. No FAISS, no Qdrant, no
   vector database. Numpy is sufficient and has zero infrastructure.

9. **Don't rebuild what's already built.** The bundle is the slowest
   thing we produce (~15 min MLX, hours on CPU). Default to publishing
   the existing `./data/rag-bundle`. Only rebuild when the docs source
   has changed. This is encoded in `scripts/publish-bundle.sh`.

## Banned dependencies

- `pandas` — replaced by `pyarrow` + `numpy`. See `atlas/make_bundle.py`
  `build_chunk_table()` and `atlas/rag_server.py` `Bundle.__init__()`
  for the patterns.
- `faiss` / `qdrant` / `chromadb` — numpy matmul suffices for 250k
  vectors. Only reconsider at 10M+ chunks or if live updates are needed.
- `joblib` — `concurrent.futures` is stdlib and sufficient.

## Recommended patterns

### Parquet read → numpy columns
```python
table = pq.read_table(path)
pubs = table.column("publication").to_numpy(zero_copy_only=False)
ids = table.column("id").to_pylist()
texts = table.column("text").to_pylist()
id_map = {cid: i for i, cid in enumerate(ids)}
```

### String contains over arrow array
```python
matches = pc.match_substring(title_col, token)  # returns bool array
boost = matches.cast("float32").to_numpy()
```

### Build parquet from lists (no DataFrame)
```python
cols: dict[str, list] = {"col_a": [], "col_b": []}
# ... fill cols ...
table = pa.table(cols)
pq.write_table(table, path)
```

### Parallel ONNX embedding
```python
def _embed_shard(model_id, prefer, texts, batch_size):
    embedder = get_embedder(model_id, prefer=prefer)
    return embedder.embed_with_progress(texts, batch_size=batch_size, show_progress=False)

with ProcessPoolExecutor(max_workers=n_workers) as pool:
    futures = {pool.submit(_embed_shard, ...): i for i, shard in enumerate(shards)}
    for f in as_completed(futures):
        results[futures[f]] = f.result()
```

### Double-checked locking for singletons
```python
_instance: Bundle | None = None
_lock = asyncio.Lock()

async def get_bundle() -> Bundle:
    global _instance
    if _instance is not None:
        return _instance
    async with _lock:
        if _instance is not None:
            return _instance
        _instance = Bundle(path)
    return _instance
```
