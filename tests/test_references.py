from unittest.mock import patch

from lib.references import (
    ReferenceDocument,
    ReferenceLoadResult,
    ReferenceMetadata,
    ReferenceSource,
    load_local_reference,
    load_local_references,
    load_remote_reference,
    load_remote_references,
)


def test_reference_source_valid_local():
    src = ReferenceSource(kind="local", value="../my-service")
    assert src.kind == "local"
    assert src.value == "../my-service"
    assert src.label is None


def test_reference_source_valid_remote():
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")
    assert src.kind == "remote"


def test_reference_source_with_label():
    src = ReferenceSource(kind="local", value="../svc", label="my service")
    assert src.label == "my service"


def test_reference_source_rejects_empty_value():
    import pytest

    with pytest.raises(ValueError, match="must not be empty"):
        ReferenceSource(kind="local", value="")


def test_reference_source_rejects_unsupported_kind():
    import pytest

    with pytest.raises(ValueError, match="unsupported"):
        ReferenceSource(kind="inline", value="something")


def test_reference_source_to_dict_omits_label():
    d = ReferenceSource(kind="local", value="../svc").to_dict()
    assert "label" not in d
    assert d == {"kind": "local", "value": "../svc"}


def test_reference_source_to_dict_includes_label():
    d = ReferenceSource(kind="local", value="../svc", label="svc").to_dict()
    assert d["label"] == "svc"


def test_reference_document_defaults():
    src = ReferenceSource(kind="local", value="../svc")
    doc = ReferenceDocument(source=src, content="# AGENTS.md\n\nRules here.")
    assert doc.source_path == "AGENTS.md"
    assert doc.version is None
    assert doc.commit_sha is None


def test_reference_document_to_dict_includes_optional_fields():
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")
    doc = ReferenceDocument(
        source=src,
        content="content",
        version="1.0",
        commit_sha="abc123",
    )
    d = doc.to_dict()
    assert d["version"] == "1.0"
    assert d["commit_sha"] == "abc123"


def test_reference_document_to_dict_omits_optional_fields():
    src = ReferenceSource(kind="local", value="../svc")
    doc = ReferenceDocument(source=src, content="content")
    d = doc.to_dict()
    assert "version" not in d
    assert "commit_sha" not in d


def test_reference_load_result_success():
    src = ReferenceSource(kind="local", value="../svc")
    doc = ReferenceDocument(source=src, content="content")
    result = ReferenceLoadResult(source=src, document=doc)
    assert result.ok
    assert result.error is None


def test_reference_load_result_failure():
    src = ReferenceSource(kind="local", value="../svc")
    result = ReferenceLoadResult(source=src, error="not found")
    assert not result.ok
    assert result.document is None


def test_reference_load_result_rejects_both_set():
    import pytest

    src = ReferenceSource(kind="local", value="../svc")
    doc = ReferenceDocument(source=src, content="content")
    with pytest.raises(ValueError, match="cannot have both"):
        ReferenceLoadResult(source=src, document=doc, error="oops")


def test_reference_load_result_rejects_neither_set():
    import pytest

    src = ReferenceSource(kind="local", value="../svc")
    with pytest.raises(ValueError, match="must have either"):
        ReferenceLoadResult(source=src)


def test_reference_load_result_to_dict_success():
    src = ReferenceSource(kind="local", value="../svc")
    doc = ReferenceDocument(source=src, content="content")
    d = ReferenceLoadResult(source=src, document=doc).to_dict()
    assert "document" in d
    assert "error" not in d


def test_reference_load_result_to_dict_failure():
    src = ReferenceSource(kind="local", value="../svc")
    d = ReferenceLoadResult(source=src, error="not found").to_dict()
    assert "error" in d
    assert "document" not in d


def test_reference_metadata_serialization():
    meta = ReferenceMetadata(
        agentskill_version="0.5.0",
        sources=[
            {"kind": "local", "value": "../svc", "source_path": "AGENTS.md"},
            {
                "kind": "remote",
                "value": "https://github.com/org/repo.git",
                "source_path": "AGENTS.md",
                "commit_sha": "abc123",
            },
        ],
    )
    d = meta.to_dict()
    assert d["agentskill_version"] == "0.5.0"
    assert len(d["references"]) == 2
    assert d["references"][0]["kind"] == "local"
    assert d["references"][1]["commit_sha"] == "abc123"


def test_reference_metadata_preserves_source_ordering():
    meta = ReferenceMetadata(
        agentskill_version="0.5.0",
        sources=[
            {"kind": "local", "value": "../a"},
            {"kind": "local", "value": "../b"},
            {"kind": "local", "value": "../c"},
        ],
    )
    d = meta.to_dict()
    assert [s["value"] for s in d["references"]] == ["../a", "../b", "../c"]


def test_reference_metadata_omits_absent_optional_fields():
    meta = ReferenceMetadata(agentskill_version="0.5.0")
    d = meta.to_dict()
    assert d["references"] == []


def test_load_local_reference_success(tmp_path):
    repo = tmp_path / "my-repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# Rules\n\nBe kind.")

    src = ReferenceSource(kind="local", value=str(repo))
    result = load_local_reference(src)

    assert result.ok
    assert result.document is not None
    assert result.document.content == "# Rules\n\nBe kind."
    assert result.document.source_path == "AGENTS.md"
    assert result.document.source is src


def test_load_local_reference_missing_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    src = ReferenceSource(kind="local", value=str(missing))
    result = load_local_reference(src)

    assert not result.ok
    assert result.document is None
    assert result.error is not None
    assert "does not exist" in result.error


def test_load_local_reference_path_is_file(tmp_path):
    file_path = tmp_path / "not-a-dir"
    file_path.write_text("hello")

    src = ReferenceSource(kind="local", value=str(file_path))
    result = load_local_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "not a directory" in result.error


def test_load_local_reference_missing_agents_md(tmp_path):
    repo = tmp_path / "empty-repo"
    repo.mkdir()

    src = ReferenceSource(kind="local", value=str(repo))
    result = load_local_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "AGENTS.md not found" in result.error


def test_load_local_reference_empty_agents_md(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("")

    src = ReferenceSource(kind="local", value=str(repo))
    result = load_local_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "empty" in result.error


def test_load_local_reference_whitespace_only_agents_md(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("   \n\n  ")

    src = ReferenceSource(kind="local", value=str(repo))
    result = load_local_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "empty" in result.error


def test_load_local_reference_unsupported_kind():
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")
    result = load_local_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "unsupported local reference source kind" in result.error


def test_load_local_references_batch_preserves_order(tmp_path):
    repo_a = tmp_path / "repo-a"
    repo_a.mkdir()
    (repo_a / "AGENTS.md").write_text("# A\n")

    repo_c = tmp_path / "repo-c"
    repo_c.mkdir()
    (repo_c / "AGENTS.md").write_text("# C\n")

    sources = [
        ReferenceSource(kind="local", value=str(repo_a)),
        ReferenceSource(kind="local", value=str(tmp_path / "missing")),
        ReferenceSource(kind="local", value=str(repo_c)),
    ]

    results = load_local_references(sources)

    assert len(results) == 3
    assert results[0].ok
    assert not results[1].ok
    assert results[2].ok
    assert results[0].document is not None
    assert results[2].document is not None
    assert results[0].document.content == "# A\n"
    assert results[2].document.content == "# C\n"


def _mock_clone_success(tmp_dir, agents_content="# Rules\n", sha="abc123def"):
    clone_dir = tmp_dir / "repo"
    clone_dir.mkdir(parents=True)
    (clone_dir / "AGENTS.md").write_text(agents_content)
    return clone_dir


def test_load_remote_reference_success(tmp_path):
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")
    _mock_clone_success(tmp_path)

    def fake_run_git(cmd, cwd=None):
        if "clone" in cmd:
            return 0, "", ""
        if "rev-parse" in cmd:
            return 0, "abc123def\n", ""
        return 1, "", "unknown command"

    with (
        patch("lib.references._run_git", side_effect=fake_run_git),
        patch("lib.references.TemporaryDirectory") as mock_tmp,
    ):
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = lambda s, *a: None
        result = load_remote_reference(src)

    assert result.ok
    assert result.document is not None
    assert result.document.content == "# Rules\n"
    assert result.document.source_path == "AGENTS.md"
    assert result.document.commit_sha == "abc123def"


def test_load_remote_reference_clone_failure(tmp_path):
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")

    def fake_run_git(cmd, cwd=None):
        if "clone" in cmd:
            return 1, "", "fatal: repository not found"
        return 1, "", ""

    with (
        patch("lib.references._run_git", side_effect=fake_run_git),
        patch("lib.references.TemporaryDirectory") as mock_tmp,
    ):
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = lambda s, *a: None
        result = load_remote_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "failed to clone" in result.error


def test_load_remote_reference_clone_timeout(tmp_path):
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")

    def fake_run_git(cmd, cwd=None):
        return 1, "", "git command timed out after 60s"

    with (
        patch("lib.references._run_git", side_effect=fake_run_git),
        patch("lib.references.TemporaryDirectory") as mock_tmp,
    ):
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = lambda s, *a: None
        result = load_remote_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "failed to clone" in result.error


def test_load_remote_reference_missing_agents_md(tmp_path):
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")
    clone_dir = tmp_path / "repo"
    clone_dir.mkdir(parents=True)

    def fake_run_git(cmd, cwd=None):
        if "clone" in cmd:
            return 0, "", ""
        if "rev-parse" in cmd:
            return 0, "abc123\n", ""
        return 1, "", ""

    with (
        patch("lib.references._run_git", side_effect=fake_run_git),
        patch("lib.references.TemporaryDirectory") as mock_tmp,
    ):
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = lambda s, *a: None
        result = load_remote_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "AGENTS.md not found" in result.error


def test_load_remote_reference_empty_agents_md(tmp_path):
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")
    _mock_clone_success(tmp_path, agents_content="")

    def fake_run_git(cmd, cwd=None):
        if "clone" in cmd:
            return 0, "", ""
        if "rev-parse" in cmd:
            return 0, "abc123\n", ""
        return 1, "", ""

    with (
        patch("lib.references._run_git", side_effect=fake_run_git),
        patch("lib.references.TemporaryDirectory") as mock_tmp,
    ):
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = lambda s, *a: None
        result = load_remote_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "empty" in result.error


def test_load_remote_reference_commit_sha_unavailable(tmp_path):
    src = ReferenceSource(kind="remote", value="https://github.com/org/repo.git")
    _mock_clone_success(tmp_path)

    def fake_run_git(cmd, cwd=None):
        if "clone" in cmd:
            return 0, "", ""
        if "rev-parse" in cmd:
            return 1, "", "not a git repo"
        return 1, "", ""

    with (
        patch("lib.references._run_git", side_effect=fake_run_git),
        patch("lib.references.TemporaryDirectory") as mock_tmp,
    ):
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = lambda s, *a: None
        result = load_remote_reference(src)

    assert result.ok
    assert result.document is not None
    assert result.document.commit_sha is None


def test_load_remote_reference_unsupported_kind():
    src = ReferenceSource(kind="local", value="../some-repo")
    result = load_remote_reference(src)

    assert not result.ok
    assert result.error is not None
    assert "unsupported remote reference source kind" in result.error


def test_load_remote_references_batch_preserves_order(tmp_path):
    src_ok = ReferenceSource(kind="remote", value="https://github.com/org/ok.git")
    src_fail = ReferenceSource(kind="remote", value="https://github.com/org/fail.git")
    src_ok2 = ReferenceSource(kind="remote", value="https://github.com/org/ok2.git")

    call_count = 0

    def fake_run_git(cmd, cwd=None):
        nonlocal call_count
        call_count += 1

        if "clone" in cmd:
            if "fail" in cmd[4]:
                return 1, "", "fatal: not found"

            clone_dir = tmp_path / "repo"
            if not clone_dir.exists():
                clone_dir.mkdir(parents=True)
            if not (clone_dir / "AGENTS.md").exists():
                (clone_dir / "AGENTS.md").write_text("# Rules\n")

            return 0, "", ""

        if "rev-parse" in cmd:
            return 0, "abc123\n", ""

        return 1, "", ""

    with (
        patch("lib.references._run_git", side_effect=fake_run_git),
        patch("lib.references.TemporaryDirectory") as mock_tmp,
    ):
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = lambda s, *a: None
        results = load_remote_references([src_ok, src_fail, src_ok2])

    assert len(results) == 3
    assert results[0].ok
    assert not results[1].ok
    assert results[2].ok
