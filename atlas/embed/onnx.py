"""ONNX Runtime backend for embedding.

Portable, works on every platform with ``onnxruntime`` installed.
On Apple Silicon, the CoreML execution provider is intentionally
NOT used here: the BGE model is unstable under CoreML for long
sequences (the second inference batch reliably triggers a SIGKILL
on M-series) and is 30-40x slower than CPU when it does run. CUDA
is honoured if the user explicitly asks for ``onnx-gpu``.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
from transformers.utils.hub import cached_file

from .base import (
    Embedder,
    l2_normalize,
    mean_pool,
)

# ONNX file to use per backend: int8 for CPU (4x faster, negligible
# quality loss for retrieval), FP32 for GPU where throughput is ample.
_ONNX_FILES = {
    False: "onnx/model_int8.onnx",
    True: "onnx/model.onnx",
}


def _resolve_model_dir(model_dir: str | Path) -> Path:
    """Resolve a model id or local path to a local directory.

    If ``model_dir`` is an existing directory, return it as-is. If
    it is a Hugging Face model id, download the full model snapshot
    (ONNX model + tokenizer + config) and return the snapshot path.
    """
    p = Path(model_dir)
    if p.is_dir():
        return p
    path = snapshot_download(model_dir)
    return Path(path)


def _providers(prefer_gpu: bool) -> list[str]:
    """Pick execution providers in order, GPU only if explicitly asked."""
    available = ort.get_available_providers()
    wanted: list[str] = []
    if prefer_gpu and "CUDAExecutionProvider" in available:
        wanted.append("CUDAExecutionProvider")
    if "CPUExecutionProvider" in available:
        wanted.append("CPUExecutionProvider")
    return wanted


class OnnxEmbedder(Embedder):
    """ONNX Runtime embedder. Portable, slow-but-stable, no special deps."""

    backend = "onnx"

    def __init__(self, model_id: str | Path, prefer_gpu: bool = False) -> None:
        self.model_id = str(model_id)
        self.resolved_dir = _resolve_model_dir(self.model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(self.resolved_dir)
        providers = _providers(prefer_gpu)
        if not providers:
            raise RuntimeError("No ONNX execution providers available")
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.intra_op_num_threads = os.cpu_count() or 4
        onnx_path = cached_file(self.model_id, _ONNX_FILES[prefer_gpu])
        self.session = ort.InferenceSession(
            str(onnx_path),
            sess_options=so,
            providers=providers,
        )
        self.active_provider = self.session.get_providers()[0]
        self._prefer_gpu = prefer_gpu
        self.dim = self.session.get_outputs()[0].shape[-1]

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        feed = {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
        }
        if "token_type_ids" in encoded:
            feed["token_type_ids"] = encoded["token_type_ids"]
        outputs = self.session.run(None, feed)
        # session.run returns Sequence[Value] where Value is
        # ndarray | SparseTensor | list | dict. The BGE model
        # always returns last_hidden_state as an ndarray first.
        hidden = outputs[0]
        assert isinstance(hidden, np.ndarray), (
            f"expected ndarray from BGE first output, got {type(hidden).__name__}"
        )
        pooled = mean_pool(hidden, encoded["attention_mask"])
        return l2_normalize(pooled)
