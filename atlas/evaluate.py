#!/usr/bin/env python3
"""Evaluate RAG quality by checking if results contain the query string."""

import argparse
from pathlib import Path

import numpy as np

from atlas.fs_server import read_publication_file, repo_root
from atlas.rag_server import Bundle

QUERIES = [
    "incident management",
    "change request",
    "problem management",
    "configuration item",
    "service catalog",
    "knowledge base",
    "SLA",
    "workflow",
    "approval",
    "notification",
]


def evaluate(
    bundle_dir: str | Path = "./data/rag-bundle",
    docs_root: str | Path = "./data/servicenow-docs/ServiceNowDocs-australia",
    prefer: str = "auto",
    queries: list[str] | None = None,
    k: int = 10,
) -> tuple[float, float]:
    bundle_dir = Path(bundle_dir).resolve()
    docs_root = Path(docs_root).resolve()

    print("Loading RAG bundle...")
    bundle = Bundle(bundle_dir, prefer=prefer)
    print(f"Bundle loaded with {len(bundle.chunks)} chunks.")

    queries = queries or QUERIES
    precisions: list[float] = []
    reciprocal_ranks: list[float] = []

    for query in queries:
        print(f"\nQuery: {query!r}")
        rag_results = bundle.search(query, top_k=k)
        print(f"  RAG top {k} retrieved.")

        relevant_flags: list[bool] = []
        for i, result in enumerate(rag_results):
            pub = result["publication"]
            file_path = result["file"]
            try:
                file_info = read_publication_file(
                    repo_root(str(docs_root)),
                    pub,
                    file_path,
                    max_chars=10000,
                )
                content = file_info["content"].lower()
                is_relevant = query.lower() in content
                relevant_flags.append(is_relevant)
                tag = "RELEVANT" if is_relevant else "irrelevant"
                print(f"    Rank {i+1}: {tag} - {pub}/{file_path}")
            except Exception as e:
                print(f"    Rank {i+1}: ERROR reading {pub}/{file_path}: {e}")
                relevant_flags.append(False)

        num_relevant = sum(relevant_flags)
        precision = num_relevant / k if k > 0 else 0.0
        precisions.append(precision)
        print(f"  Precision@{k}: {precision:.3f} ({num_relevant}/{k})")

        rr = 0.0
        for i, rel in enumerate(relevant_flags):
            if rel:
                rr = 1.0 / (i + 1)
                break
        reciprocal_ranks.append(rr)
        print(f"  Reciprocal rank: {rr:.3f}")

    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY (relevance = contains query string)")
    print("=" * 50)
    m_p = float(np.mean(precisions))
    s_p = float(np.std(precisions))
    m_r = float(np.mean(reciprocal_ranks))
    s_r = float(np.std(reciprocal_ranks))
    print(f"Mean Precision@{k}: {m_p:.3f} ± {s_p:.3f}")
    print(f"Mean Reciprocal Rank: {m_r:.3f} ± {s_r:.3f}")
    print(f"Queries with zero precision: {sum(1 for p in precisions if p == 0)}")
    print(f"Queries with zero reciprocal rank: {sum(1 for rr in reciprocal_ranks if rr == 0)}")
    return m_p, m_r


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate RAG quality")
    p.add_argument("--bundle", default="./data/rag-bundle", help="Path to RAG bundle directory")
    p.add_argument("--docs", default="./data/servicenow-docs/ServiceNowDocs-australia", help="Path to docs clone")
    p.add_argument("--prefer", choices=["auto", "apple", "nvidia", "cpu"], default="auto", help="Embedding backend preference")
    p.add_argument("--top-k", type=int, default=10, help="Number of results to evaluate per query")
    args = p.parse_args()
    evaluate(bundle_dir=args.bundle, docs_root=args.docs, prefer=args.prefer, k=args.top_k)


if __name__ == "__main__":
    main()
