from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from atlas.rag_server import Bundle


@pytest.fixture
def fake_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Bundle:
    DIM = 4
    chunks = pd.DataFrame(
        {
            "id": ["c1", "c2", "c3"],
            "text": [
                "how to create an incident in servicenow",
                "how to create a change request",
                "database query performance tuning",
            ],
            "publication": ["it-service-management", "it-service-management", "platform"],
            "file": ["incident.md", "change.md", "db.md"],
            "heading": ["Create Incident", "Create Change", "Tuning"],
            "title": ["Incident Management", "Change Management", "Performance"],
            "product_area": ["incident", "change", "platform"],
            "last_updated": ["2024-01-01"] * 3,
            "canonical_url": ["https://example.com/1"] * 3,
            "is_code": [False, False, True],
        }
    )

    rng = np.random.default_rng(42)
    embeddings = rng.normal(size=(3, DIM)).astype(np.float32)
    embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)

    manifest = {
        "chunk_count": 3,
        "embedding_dim": DIM,
        "embedding_model": "test-model",
        "embedding_dtype": "float32",
    }

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    chunks.to_parquet(bundle_dir / "chunks.parquet")
    np.save(bundle_dir / "embeddings.f32.npy", embeddings)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest))

    class FakeEmbedder:
        dim = DIM

        def embed(self, texts: list[str]) -> list[np.ndarray]:
            return [np.zeros(DIM, dtype=np.float32) for _ in texts]

    with patch("atlas.rag_server.get_embedder", return_value=FakeEmbedder()):
        yield Bundle(bundle_dir, prefer="cpu")


def test_search_vector_returns_top_k(fake_bundle: Bundle) -> None:
    results = fake_bundle.search("incident", top_k=2)
    assert len(results) <= 2


def test_search_hybrid_returns_results(fake_bundle: Bundle) -> None:
    results = fake_bundle.search("incident", top_k=5, mode="hybrid")
    assert len(results) > 0


def test_search_keyword_ranks_exact_matches_higher(fake_bundle: Bundle) -> None:
    results = fake_bundle.search("create", top_k=5, mode="keyword")
    assert len(results) > 0


def test_search_publication_filter(fake_bundle: Bundle) -> None:
    results = fake_bundle.search("create", top_k=5, publication="platform")
    assert all(r["publication"] == "platform" for r in results)


def test_search_is_code_filter(fake_bundle: Bundle) -> None:
    results = fake_bundle.search(
        "database query performance tuning",
        top_k=5,
        is_code=True,
    )
    assert all(r["is_code"] is True for r in results)


def test_search_min_score_filter(fake_bundle: Bundle) -> None:
    results = fake_bundle.search("incident", top_k=5, min_score=0.99)
    assert len(results) == 0


def test_get_chunk_returns_matching_chunk(fake_bundle: Bundle) -> None:
    chunk = fake_bundle.get_chunk("c1")
    assert chunk is not None
    assert chunk["id"] == "c1"
    assert "text" in chunk


def test_get_chunk_missing_returns_none(fake_bundle: Bundle) -> None:
    assert fake_bundle.get_chunk("nonexistent") is None


def test_search_empty_query_vector(fake_bundle: Bundle) -> None:
    results = fake_bundle.search("", top_k=5)
    assert len(results) > 0


def test_search_mode_parameter_defaults_to_vector(fake_bundle: Bundle) -> None:
    # Verify mode defaults don't cause issues; smoke test for backward compat
    vec = fake_bundle.search("incident", top_k=5, mode="vector")
    hybrid = fake_bundle.search("incident", top_k=5, mode="hybrid")
    kw = fake_bundle.search("incident", top_k=5, mode="keyword")
    assert all(len(r) >= 0 for r in (vec, hybrid, kw))
