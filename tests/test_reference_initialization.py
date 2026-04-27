"""Tests for reference initialization and metadata."""

import json

from lib.reference_initialization import (
    AGENTSKILL_VERSION,
    build_reference_metadata,
    initialize_from_references,
    is_empty_target,
    render_reference_metadata_block,
    successful_reference_documents,
)
from lib.references import ReferenceDocument, ReferenceLoadResult, ReferenceSource


def _src(kind: str = "local", value: str = "../ref") -> ReferenceSource:
    return ReferenceSource(kind=kind, value=value)


def _doc(
    content: str = "# AGENTS.md\n\nUse pytest.",
    source: ReferenceSource | None = None,
    commit_sha: str | None = None,
    source_path: str = "AGENTS.md",
) -> ReferenceDocument:
    if source is None:
        source = _src()

    return ReferenceDocument(
        source=source, content=content, source_path=source_path, commit_sha=commit_sha
    )


def _analysis(**kwargs) -> dict:
    return dict(kwargs)


def test_is_empty_target_zero_files():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": []})

    assert is_empty_target(target) is True


def test_is_empty_target_no_scan():
    target = _analysis()

    assert is_empty_target(target) is True


def test_is_empty_target_with_files():
    target = _analysis(
        scan={"summary": {"total_files": 3}, "tree": [{"path": "main.py"}]}
    )

    assert is_empty_target(target) is False


def test_is_empty_target_with_tree():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": [{"path": "x.py"}]})

    assert is_empty_target(target) is False


def test_is_empty_target_with_config():
    target = _analysis(
        scan={"summary": {"total_files": 0}, "tree": []},
        config={"python": {"linter": {"name": "ruff"}}},
    )

    assert is_empty_target(target) is False


def test_is_empty_target_with_git():
    target = _analysis(
        scan={"summary": {"total_files": 0}, "tree": []},
        git={"commit_patterns": {"fix": 5}},
    )

    assert is_empty_target(target) is False


def test_build_reference_metadata_local():
    doc = _doc(source=_src(kind="local", value="../service-template"))
    meta = build_reference_metadata([doc], "0.5.0")
    d = meta.to_dict()

    assert d["agentskill_version"] == "0.5.0"
    assert len(d["references"]) == 1
    assert d["references"][0]["kind"] == "local"
    assert d["references"][0]["value"] == "../service-template"
    assert d["references"][0]["source_path"] == "AGENTS.md"


def test_build_reference_metadata_remote_with_sha():
    doc = _doc(
        source=_src(kind="remote", value="https://github.com/org/repo.git"),
        commit_sha="abc123",
    )
    meta = build_reference_metadata([doc], "0.5.0")
    d = meta.to_dict()

    assert d["references"][0]["commit_sha"] == "abc123"


def test_build_reference_metadata_no_timestamp():
    doc = _doc()
    meta = build_reference_metadata([doc], "0.5.0")
    d = meta.to_dict()

    assert "timestamp" not in d
    assert "timestamp" not in d["references"][0]


def test_build_reference_metadata_preserves_order():
    docs = [
        _doc(source=_src(value="ref-a")),
        _doc(source=_src(value="ref-b")),
        _doc(source=_src(value="ref-c")),
    ]
    meta = build_reference_metadata(docs, "0.5.0")
    d = meta.to_dict()

    assert [r["value"] for r in d["references"]] == ["ref-a", "ref-b", "ref-c"]


def test_render_metadata_block_format():
    doc = _doc()
    meta = build_reference_metadata([doc], "0.5.0")
    block = render_reference_metadata_block(meta)

    assert block.startswith("<!-- agentskill-metadata\n")
    assert block.endswith("\n-->")
    json_body = block.split("\n", 1)[1].rsplit("\n-->", 1)[0]
    parsed = json.loads(json_body)
    assert "agentskill_version" in parsed
    assert "references" in parsed


def test_render_metadata_block_roundtrip():
    doc = _doc(
        source=_src(kind="remote", value="https://github.com/org/repo.git"),
        commit_sha="deadbeef",
    )
    meta = build_reference_metadata([doc], "0.5.0")
    block = render_reference_metadata_block(meta)
    json_body = block.split("\n", 1)[1].rsplit("\n-->", 1)[0]
    parsed = json.loads(json_body)

    assert parsed["agentskill_version"] == "0.5.0"
    assert parsed["references"][0]["commit_sha"] == "deadbeef"


def test_successful_reference_documents():
    src_a = _src(value="a")
    src_b = _src(value="b")
    doc_a = _doc(source=src_a)
    ok = ReferenceLoadResult(source=src_a, document=doc_a)
    fail = ReferenceLoadResult(source=src_b, error="not found")
    docs = successful_reference_documents([ok, fail])

    assert len(docs) == 1
    assert docs[0].source.value == "a"


def test_initialize_empty_target_reference_derived():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": []})
    doc = _doc(content="## Testing\n\nUse pytest.")
    result = initialize_from_references(target, [doc])

    assert result.is_reference_derived is True
    assert result.adapted_references
    assert result.metadata is not None
    assert result.usable_reference_count == 1


def test_initialize_non_empty_target_not_reference_derived():
    target = _analysis(
        scan={
            "summary": {"total_files": 3, "languages": ["python"]},
            "tree": [{"path": "main.py"}],
        }
    )
    doc = _doc(content="## Testing\n\nUse pytest.")
    result = initialize_from_references(target, [doc])

    assert result.is_reference_derived is False
    assert result.metadata is not None
    assert result.adapted_references


def test_initialize_multiple_references_preserve_order():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": []})
    docs = [
        _doc(source=_src(value="a"), content="## A\n\nUse A."),
        _doc(source=_src(value="b"), content="## B\n\nUse B."),
        _doc(source=_src(value="c"), content="## C\n\nUse C."),
    ]
    result = initialize_from_references(target, docs)

    assert [r.source.value for r in result.adapted_references] == ["a", "b", "c"]
    meta_refs = result.metadata.to_dict()["references"]
    assert [r["value"] for r in meta_refs] == ["a", "b", "c"]


def test_initialize_includes_questions():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": []})
    doc = _doc(content="## Testing\n\nUse pytest for tests.")
    result = initialize_from_references(target, [doc])

    assert isinstance(result.questions, list)


def test_initialize_no_documents_warning():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": []})
    result = initialize_from_references(target, [])

    assert result.usable_reference_count == 0
    assert "no reference documents provided" in result.warnings


def test_initialize_agentskill_version_in_metadata():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": []})
    doc = _doc()
    result = initialize_from_references(target, [doc], agentskill_version="1.2.3")

    assert result.metadata.agentskill_version == "1.2.3"


def test_initialize_default_agentskill_version():
    target = _analysis(scan={"summary": {"total_files": 0}, "tree": []})
    doc = _doc()
    result = initialize_from_references(target, [doc])

    assert result.metadata.agentskill_version == AGENTSKILL_VERSION
