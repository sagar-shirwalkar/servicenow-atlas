from __future__ import annotations

import platform
from pathlib import Path

import numpy as np
import pytest

from atlas.embed.base import (
    _CANONICAL_CHOICE,
    _read_config_backend,
    has_mlx,
    has_nvidia_gpu,
    has_onnxruntime_gpu,
    is_apple_silicon,
    l2_normalize,
    load_embeddings,
    mean_pool,
    resolve_backend,
)


class TestCanonicalChoice:
    def test_apple_maps_to_mlx(self) -> None:
        assert _CANONICAL_CHOICE["apple"] == "mlx"

    def test_nvidia_maps_to_onnx_gpu(self) -> None:
        assert _CANONICAL_CHOICE["nvidia"] == "onnx-gpu"

    def test_cpu_maps_to_onnx_cpu(self) -> None:
        assert _CANONICAL_CHOICE["cpu"] == "onnx-cpu"

    def test_aliases_are_case_preserved(self) -> None:
        assert _CANONICAL_CHOICE["gpu"] == "onnx-gpu"
        assert _CANONICAL_CHOICE["cuda"] == "onnx-gpu"


class TestIsAppleSilicon:
    def test_returns_true_on_arm64_mac(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        assert is_apple_silicon() is True

    def test_returns_false_on_intel_mac(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        assert is_apple_silicon() is False

    def test_returns_false_on_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert is_apple_silicon() is False


class TestReadConfigBackend:
    def test_returns_none_when_no_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "is_file", lambda _: False)
        assert _read_config_backend() is None

    def test_returns_prefer_from_backend_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = tmp_path / ".config" / "atlas.toml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("[backend]\nprefer = \"apple\"\n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _read_config_backend() == "apple"

    def test_ignores_other_sections(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = tmp_path / ".config" / "atlas.toml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("[other]\nprefer = \"nvidia\"\n[backend]\nprefer = \"cpu\"\n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _read_config_backend() == "cpu"

    def test_ignores_comments_and_blanks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = tmp_path / ".config" / "atlas.toml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("# comment\n\n[backend]\nprefer = \"mlx\"\n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _read_config_backend() == "mlx"

    def test_returns_none_on_io_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "is_file", lambda _: True)
        monkeypatch.setattr(Path, "read_text", lambda _: (_ for _ in ()).throw(OSError("denied")))
        assert _read_config_backend() is None


class TestHasNvidiaGpu:
    def test_returns_false_when_nvidia_smi_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _: None)
        assert has_nvidia_gpu() is False

    def test_returns_true_when_gpu_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/nvidia-smi")

        class FakeResult:
            returncode = 0
            stdout = "GPU 0: Tesla T4"

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        assert has_nvidia_gpu() is True

    def test_returns_false_when_no_gpu_in_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/nvidia-smi")

        class FakeResult:
            returncode = 0
            stdout = "No compatible devices"

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        assert has_nvidia_gpu() is False


class TestHasMlx:
    def test_returns_false_when_not_importable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def fake_import(name, *a, **kw):
            if name == "mlx.core":
                raise ImportError("no mlx")
            return original_import(name, *a, **kw)

        monkeypatch.setattr("builtins.__import__", fake_import)
        assert has_mlx() is False


class TestHasOnnxruntimeGpu:
    def test_returns_false_when_not_importable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def fake_import(name, *a, **kw):
            if name == "onnxruntime":
                raise ImportError("no ort")
            return original_import(name, *a, **kw)

        monkeypatch.setattr("builtins.__import__", fake_import)
        assert has_onnxruntime_gpu() is False


class TestResolveBackend:
    def test_auto_picks_mlx_on_apple_silicon(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.is_apple_silicon", lambda: True)
        monkeypatch.setattr("atlas.embed.base.has_mlx", lambda: True)
        backend, reason = resolve_backend("auto")
        assert backend == "mlx"
        assert "Apple Silicon" in reason

    def test_auto_picks_onnx_gpu_on_nvidia(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.is_apple_silicon", lambda: False)
        monkeypatch.setattr("atlas.embed.base.has_nvidia_gpu", lambda: True)
        monkeypatch.setattr("atlas.embed.base.has_onnxruntime_gpu", lambda: True)
        backend, reason = resolve_backend("auto")
        assert backend == "onnx-gpu"
        assert "NVIDIA" in reason

    def test_auto_falls_to_onnx_cpu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.is_apple_silicon", lambda: False)
        monkeypatch.setattr("atlas.embed.base.has_nvidia_gpu", lambda: False)
        backend, reason = resolve_backend("auto")
        assert backend == "onnx-cpu"

    def test_user_prefer_apple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.has_mlx", lambda: True)
        monkeypatch.setattr("atlas.embed.base.is_apple_silicon", lambda: True)
        backend, _reason = resolve_backend("apple")
        assert backend == "mlx"

    def test_user_prefer_apple_falls_back_when_mlx_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.has_mlx", lambda: False)
        monkeypatch.setattr("atlas.embed.base.is_apple_silicon", lambda: True)
        backend, reason = resolve_backend("apple")
        assert backend == "onnx-cpu"
        assert "fallback" in reason

    def test_user_prefer_nvidia(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.has_nvidia_gpu", lambda: True)
        monkeypatch.setattr("atlas.embed.base.has_onnxruntime_gpu", lambda: True)
        backend, _reason = resolve_backend("nvidia")
        assert backend == "onnx-gpu"

    def test_user_prefer_nvidia_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.has_nvidia_gpu", lambda: False)
        backend, reason = resolve_backend("nvidia")
        assert backend == "onnx-cpu"
        assert "fallback" in reason

    def test_user_prefer_cpu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backend, reason = resolve_backend("cpu")
        assert backend == "onnx-cpu"
        assert "user requested" in reason

    def test_env_var_overrides_prefer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.has_nvidia_gpu", lambda: True)
        monkeypatch.setattr("atlas.embed.base.has_onnxruntime_gpu", lambda: True)
        monkeypatch.setenv("ATLAS_EMBED_BACKEND", "nvidia")
        backend, _reason = resolve_backend(None)
        assert backend == "onnx-gpu"

    def test_unknown_choice_falls_to_auto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("atlas.embed.base.is_apple_silicon", lambda: False)
        monkeypatch.setattr("atlas.embed.base.has_nvidia_gpu", lambda: False)
        backend, _reason = resolve_backend("foobar")
        assert backend == "onnx-cpu"


class TestLoadEmbeddings:
    def test_loads_f16_and_converts_to_f32(self, tmp_path: Path) -> None:
        arr = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float16)
        np.save(tmp_path / "embeddings.f16.npy", arr)
        loaded = load_embeddings(tmp_path)
        assert loaded.dtype == np.float32
        assert np.allclose(loaded, arr.astype(np.float32))

    def test_loads_f32_when_f16_missing(self, tmp_path: Path) -> None:
        arr = np.array([[0.1, 0.2]], dtype=np.float32)
        np.save(tmp_path / "embeddings.f32.npy", arr)
        loaded = load_embeddings(tmp_path)
        assert loaded.dtype == np.float32
        assert np.allclose(loaded, arr)

    def test_raises_when_no_embeddings(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No embeddings"):
            load_embeddings(tmp_path)


class TestMeanPool:
    def test_mean_pool_basic(self) -> None:
        hidden = np.array([[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]], dtype=np.float32)
        mask = np.array([[1, 1, 0]], dtype=np.float32)
        result = mean_pool(hidden, mask)
        expected = np.array([[2.0, 3.0]], dtype=np.float32)
        assert np.allclose(result, expected)

    def test_mean_pool_all_masked(self) -> None:
        hidden = np.array([[[1.0, 2.0]]], dtype=np.float32)
        mask = np.array([[0]], dtype=np.float32)
        result = mean_pool(hidden, mask)
        assert np.allclose(result, np.array([[0.0, 0.0]]))


class TestL2Normalize:
    def test_normalize_unit_vector(self) -> None:
        x = np.array([[3.0, 4.0]], dtype=np.float32)
        result = l2_normalize(x)
        expected = np.array([[0.6, 0.8]], dtype=np.float32)
        assert np.allclose(result, expected)

    def test_normalize_zero_vector(self) -> None:
        x = np.array([[0.0, 0.0]], dtype=np.float32)
        result = l2_normalize(x)
        assert np.allclose(result, np.array([[0.0, 0.0]]))
