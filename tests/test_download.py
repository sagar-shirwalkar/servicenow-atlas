from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from atlas.download import (
    _existing_bundle_backup,
    _extract,
    _sha256,
    find_bundle_asset,
    resolve_release,
)

# ── find_bundle_asset ─────────────────────────────────────────────────────


class TestFindBundleAsset:
    def test_finds_tar_gz(self) -> None:
        release = {"assets": [{"name": "bundle.tar.gz"}, {"name": "readme.txt"}]}
        asset = find_bundle_asset(release)
        assert asset["name"] == "bundle.tar.gz"

    def test_finds_zip(self) -> None:
        release = {"assets": [{"name": "bundle.zip"}]}
        asset = find_bundle_asset(release)
        assert asset["name"] == "bundle.zip"

    def test_raises_when_no_asset(self) -> None:
        release = {"assets": [{"name": "readme.txt"}]}
        with pytest.raises(RuntimeError, match="No bundle asset"):
            find_bundle_asset(release)

    def test_raises_on_empty_assets(self) -> None:
        with pytest.raises(RuntimeError, match="No bundle asset"):
            find_bundle_asset({"assets": []})


# ── _sha256 ────────────────────────────────────────────────────────────────


class TestSha256:
    def test_computes_correct_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert _sha256(f) == expected

    def test_large_file(self, tmp_path: Path) -> None:
        f = tmp_path / "large.bin"
        f.write_bytes(b"a" * (2 << 20))  # 2 MB
        h = _sha256(f)
        assert len(h) == 64
        assert h == "5256ec18f11624025905d057d6befb03d77b243511ac5f77ed5e0221ce6d84b5"


# ── _extract ────────────────────────────────────────────────────────────────


class TestExtract:
    def test_extracts_tar_gz(self, tmp_path: Path) -> None:
        archive = tmp_path / "bundle.tar.gz"
        target = tmp_path / "out"
        inner = tmp_path / "inner.txt"
        inner.write_text("content")
        with tarfile.open(archive, "w:gz") as tf:
            tf.add(inner, arcname="inner.txt")
        _extract(archive, target)
        assert (target / "inner.txt").is_file()
        assert (target / "inner.txt").read_text() == "content"

    def test_raises_on_unsupported_format(self, tmp_path: Path) -> None:
        archive = tmp_path / "bundle.unknown"
        archive.write_text("")
        with pytest.raises(RuntimeError, match="Unsupported archive format"):
            _extract(archive, tmp_path / "out")


# ── resolve_release ─────────────────────────────────────────────────────────


class TestResolveRelease:
    def test_resolves_by_tag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                return json.dumps({"tag_name": "v1", "name": "Release 1"}).encode()

            def decode(self, enc):
                return json.dumps({"tag_name": "v1", "name": "Release 1"})

        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=30: FakeResp(),
        )
        release = resolve_release("owner/repo", "v1")
        assert release["tag_name"] == "v1"

    def test_resolves_latest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                return json.dumps({"tag_name": "latest", "name": "Latest Release"}).encode()

            def decode(self, enc):
                return json.dumps({"tag_name": "latest", "name": "Latest Release"})

        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=30: FakeResp(),
        )
        release = resolve_release("owner/repo", None)
        assert release["tag_name"] == "latest"


# ── _existing_bundle_backup ────────────────────────────────────────────────


class TestExistingBundleBackup:
    def test_skips_when_no_manifest(self, tmp_path: Path) -> None:
        output = tmp_path / "bundle"
        output.mkdir()
        backups = tmp_path / "backups"
        _existing_bundle_backup(output, backups)
        # should not raise; backup dir should not have been created
        assert not backups.exists() or not list(backups.iterdir())

    def test_skips_when_no_backup_root(self, tmp_path: Path) -> None:
        output = tmp_path / "bundle"
        output.mkdir()
        (output / "manifest.json").write_text("{}")
        _existing_bundle_backup(output, Path())
        # no backup dir; should return early
