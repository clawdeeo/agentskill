from lib.references import (
    ReferenceDocument,
    ReferenceLoadResult,
    ReferenceMetadata,
    ReferenceSource,
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
