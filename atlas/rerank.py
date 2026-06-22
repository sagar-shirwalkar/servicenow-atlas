from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

from .log import get_logger

MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
_ONNX_FILE = "onnx/model.onnx"

logger = get_logger()


class CrossEncoderReranker:
    """MiniLM-L6-v2 cross-encoder re-ranker running on ONNX Runtime.

    Loaded once, then ``.rerank(query, candidates, top_k)`` scores
    every candidate via joint query+passage encoding and returns the
    top-k re-sorted by cross-encoder logit.
    """

    def __init__(self, model_id: str = MODEL_ID) -> None:
        self.model_id = model_id
        resolved = Path(snapshot_download(model_id))
        onnx_path = resolved / _ONNX_FILE
        if not onnx_path.is_file():
            raise FileNotFoundError(f"ONNX model not found at {onnx_path}")
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.intra_op_num_threads = 0  # let ORT decide
        self.session = ort.InferenceSession(str(onnx_path), sess_options=so)
        self.tokenizer = AutoTokenizer.from_pretrained(str(resolved))
        logger.info(
            "Cross-encoder loaded",
            model_id=model_id,
            provider=self.session.get_providers()[0],
        )

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
        batch_size: int = 32,
    ) -> list[dict]:
        if not candidates:
            return []

        texts = [c["text"] for c in candidates]
        pairs = [(query, t) for t in texts]
        scores = self._score_pairs(pairs, batch_size)

        order = np.argsort(-scores)
        results: list[dict] = []
        for i in order[:top_k]:
            c = candidates[i]
            results.append({**c, "ce_score": float(scores[i])})
        return results

    def _score_pairs(self, pairs: list[tuple[str, str]], batch_size: int) -> np.ndarray:
        all_scores: list[np.ndarray] = []
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            queries, passages = zip(*batch, strict=True)
            encoded = self.tokenizer(
                list(queries),
                list(passages),
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="np",
            )
            feed = {
                "input_ids": encoded["input_ids"].astype(np.int64),
                "attention_mask": encoded["attention_mask"].astype(np.int64),
                "token_type_ids": encoded.get(
                    "token_type_ids",
                    np.zeros_like(encoded["input_ids"]),
                ).astype(np.int64),
            }
            logits = self.session.run(None, feed)[0]
            all_scores.append(logits.squeeze(-1))
        return np.concatenate(all_scores)
