#!/usr/bin/env python3
"""Evaluate RAG quality by checking if results contain the query string."""

import sys
import os
import numpy as np
from pathlib import Path

sys.path.insert(0, os.getcwd())

from atlas.rag_server import Bundle
from atlas.fs_server import read_publication_file, _repo_root

def evaluate():
    # Initialize
    bundle_dir = Path('./data/rag-bundle')
    docs_root = Path('./data/servicenow-docs/ServiceNowDocs-australia')
    
    print("Loading RAG bundle...")
    bundle = Bundle(bundle_dir, prefer='mlx')
    print(f"Bundle loaded with {len(bundle.chunks)} chunks.")
    
    # Test queries
    queries = [
        "incident management",
        "change request",
        "problem management",
        "configuration item",
        "service catalog",
        "knowledge base",
        "SLA",
        "workflow",
        "approval",
        "notification"
    ]
    
    k = 10
    precisions = []
    reciprocal_ranks = []
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        
        # RAG search
        rag_results = bundle.search(query, top_k=k)
        print(f"  RAG top {k} retrieved.")
        
        # Relevance judgment: does the file contain the query string (case-insensitive)?
        relevant_flags = []
        for i, result in enumerate(rag_results):
            pub = result['publication']
            file_path = result['file']
            try:
                # Read the file content
                file_info = read_publication_file(
                    _repo_root(str(docs_root)),
                    pub,
                    file_path,
                    max_chars=10000  # Read enough to check for query
                )
                content = file_info['content'].lower()
                query_lower = query.lower()
                is_relevant = query_lower in content
                relevant_flags.append(is_relevant)
                if is_relevant:
                    print(f"    Rank {i+1}: RELEVANT - {pub}/{file_path}")
                else:
                    print(f"    Rank {i+1}: irrelevant - {pub}/{file_path}")
            except Exception as e:
                print(f"    Rank {i+1}: ERROR reading {pub}/{file_path}: {e}")
                relevant_flags.append(False)
        
        # Precision@k: fraction of RAG results that are relevant
        num_relevant = sum(relevant_flags)
        precision = num_relevant / k if k > 0 else 0.0
        precisions.append(precision)
        print(f"  Precision@{k}: {precision:.3f} ({num_relevant}/{k})")
        
        # Reciprocal rank: 1 / rank of first relevant result
        rr = 0.0
        for i, rel in enumerate(relevant_flags):
            if rel:
                rr = 1.0 / (i + 1)
                break
        reciprocal_ranks.append(rr)
        print(f"  Reciprocal rank: {rr:.3f}")
    
    # Summary
    print("\n" + "="*50)
    print("EVALUATION SUMMARY (relevance = contains query string)")
    print("="*50)
    print(f"Mean Precision@{k}: {np.mean(precisions):.3f} ± {np.std(precisions):.3f}")
    print(f"Mean Reciprocal Rank: {np.mean(reciprocal_ranks):.3f} ± {np.std(reciprocal_ranks):.3f}")
    
    # Additional stats
    print(f"\nQueries with zero precision: {sum(1 for p in precisions if p == 0)}")
    print(f"Queries with zero reciprocal rank: {sum(1 for rr in reciprocal_ranks if rr == 0)}")

if __name__ == '__main__':
    evaluate()
