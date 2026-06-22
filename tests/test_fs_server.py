from __future__ import annotations

from pathlib import Path

import pytest

from atlas.fs_server import (
    _parse_md,
    _preview_line,
    full_text_search,
    get_release_info,
    list_publication_files,
    list_publications,
    read_publication_file,
    repo_root,
)

# ── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def docs_tree(tmp_path: Path) -> Path:
    """Create a mock ServiceNowDocs clone with 2 publications, 3 files."""
    root = tmp_path / "servicenow-docs"
    md = root / "markdown"
    it = md / "it-service-management"
    hr = md / "hr-service-delivery"
    it.mkdir(parents=True)
    hr.mkdir(parents=True)

    (it / "incident-management.md").write_text(
        "---\ntitle: Incident Management\nproduct_area: incident\n---\n\n"
        "How to create an incident in ServiceNow."
    )
    (it / "change-management.md").write_text(
        "---\ntitle: Change Management\nproduct_area: change\n---\n\n"
        "How to create a change request."
    )
    (hr / "onboarding.md").write_text(
        "---\ntitle: Employee Onboarding\nproduct_area: hr\n---\n\n"
        "Welcome to the company!"
    )
    return root


# ── repo_root ─────────────────────────────────────────────────────────────


class TestRepoRoot:
    def test_valid_root(self, docs_tree: Path) -> None:
        root = repo_root(str(docs_tree))
        assert root == docs_tree.resolve()

    def test_missing_markdown_dir(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No 'markdown/' directory"):
            repo_root(str(tmp_path))


# ── _parse_md ──────────────────────────────────────────────────────────────


class TestParseMd:
    def test_full_frontmatter(self, docs_tree: Path) -> None:
        f = docs_tree / "markdown" / "it-service-management" / "incident-management.md"
        parsed = _parse_md(f)
        assert parsed["frontmatter"]["title"] == "Incident Management"
        assert parsed["frontmatter"]["product_area"] == "incident"
        assert "create an incident" in parsed["content"]

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "plain.md"
        f.write_text("Just content.")
        parsed = _parse_md(f)
        assert parsed["frontmatter"] == {}
        assert parsed["content"] == "Just content."

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_text("---\nunparseable: [\n---\nbody")
        parsed = _parse_md(f)
        # malformed YAML should not crash; returns empty frontmatter
        assert "content" in parsed


# ── list_publications ──────────────────────────────────────────────────────


class TestListPublications:
    def test_returns_all_publications(self, docs_tree: Path) -> None:
        pubs = list_publications(docs_tree)
        names = {p["name"] for p in pubs}
        assert names == {"it-service-management", "hr-service-delivery"}

    def test_includes_file_counts(self, docs_tree: Path) -> None:
        pubs = {p["name"]: p["file_count"] for p in list_publications(docs_tree)}
        assert pubs["it-service-management"] == 2
        assert pubs["hr-service-delivery"] == 1


# ── list_publication_files ─────────────────────────────────────────────────


class TestListPublicationFiles:
    def test_lists_files_with_metadata(self, docs_tree: Path) -> None:
        files = list_publication_files(docs_tree, "it-service-management")
        assert len(files) == 2
        titles = {f["title"] for f in files}
        assert titles == {"Incident Management", "Change Management"}

    def test_raises_on_missing_publication(self, docs_tree: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Publication not found"):
            list_publication_files(docs_tree, "nonexistent")


# ── read_publication_file ──────────────────────────────────────────────────


class TestReadPublicationFile:
    def test_reads_file_content(self, docs_tree: Path) -> None:
        info = read_publication_file(docs_tree, "it-service-management", "incident-management.md")
        assert info["publication"] == "it-service-management"
        assert info["file"] == "incident-management.md"
        assert info["frontmatter"]["title"] == "Incident Management"
        assert "create an incident" in info["content"]

    def test_truncates_long_content(self, docs_tree: Path) -> None:
        info = read_publication_file(docs_tree, "it-service-management", "incident-management.md", max_chars=10)
        assert info["truncated"] is True
        assert len(info["content"]) <= 10

    def test_path_traversal_blocked(self, docs_tree: Path) -> None:
        with pytest.raises(ValueError, match="Path traversal blocked"):
            read_publication_file(docs_tree, "it-service-management", "../../etc/passwd")

    def test_raises_on_missing_file(self, docs_tree: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            read_publication_file(docs_tree, "it-service-management", "missing.md")


# ── _preview_line ──────────────────────────────────────────────────────────


class TestPreviewLine:
    def test_returns_context_around_line(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("line1\nline2\nline3\nline4\nline5\n")
        preview = _preview_line(f, 3)  # line 3, 1 line context
        assert "line2" in preview
        assert "line3" in preview
        assert "line4" in preview

    def test_clamps_at_start_of_file(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("first\nsecond\n")
        preview = _preview_line(f, 1)
        assert "first" in preview
        assert "second" in preview

    def test_clamps_at_end_of_file(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("line1\nline2\n")
        preview = _preview_line(f, 2)
        assert "line1" in preview
        assert "line2" in preview

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        preview = _preview_line(tmp_path / "nonexistent.md", 1)
        assert preview == ""


# ── full_text_search ───────────────────────────────────────────────────────


class TestFullTextSearch:
    def test_finds_matching_text(self, docs_tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/rg")

        class FakeProc:
            returncode = 0
            stdout = (
                f"{docs_tree}/markdown/it-service-management/incident-management.md:3:How to create an incident"
            )

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeProc())
        results = full_text_search(docs_tree, "incident")
        assert len(results) >= 1
        assert "incident-management.md" in results[0]["file"]

    def test_raises_when_rg_missing(self, docs_tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _: None)
        with pytest.raises(RuntimeError, match="ripgrep"):
            full_text_search(docs_tree, "test")

    def test_scoped_search(self, docs_tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/rg")

        class FakeProc:
            returncode = 0
            stdout = f"{docs_tree}/markdown/hr-service-delivery/onboarding.md:3:Welcome"

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeProc())
        results = full_text_search(docs_tree, "Welcome", scope="hr-service-delivery")
        assert len(results) == 1
        assert "onboarding.md" in results[0]["file"]

    def test_raises_on_missing_scope(self, docs_tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/rg")
        with pytest.raises(FileNotFoundError, match="Scope not found"):
            full_text_search(docs_tree, "test", scope="nonexistent")


# ── get_release_info ───────────────────────────────────────────────────────


class TestGetReleaseInfo:
    def test_returns_git_metadata(self, docs_tree: Path) -> None:
        """Create a real git repo and verify get_release_info works."""
        import subprocess

        subprocess.run(["git", "init"], cwd=str(docs_tree), check=True, capture_output=True, timeout=10)
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@test.com", "commit", "--allow-empty", "-m", "init"],
            cwd=str(docs_tree),
            check=True,
            capture_output=True,
            timeout=10,
        )
        info = get_release_info(docs_tree)
        assert "sha" in info
        assert len(info["sha"]) == 40
        assert info["branch"] == "main" or info["branch"] == "master"
        assert info["file_count"] >= 2
