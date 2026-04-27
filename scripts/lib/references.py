"""Reference repository data models for 0.5.0 reference loading."""

from dataclasses import dataclass, field
from pathlib import Path

from common.fs import read_text

REFERENCE_KIND_LOCAL = "local"
REFERENCE_KIND_REMOTE = "remote"
SUPPORTED_REFERENCE_KINDS = {REFERENCE_KIND_LOCAL, REFERENCE_KIND_REMOTE}
REFERENCE_AGENTS_FILENAME = "AGENTS.md"


@dataclass(frozen=True)
class ReferenceSource:
    kind: str
    value: str
    label: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in SUPPORTED_REFERENCE_KINDS:
            raise ValueError(f"unsupported reference kind: {self.kind!r}")

        if not self.value:
            raise ValueError("reference value must not be empty")

    def to_dict(self) -> dict:
        data: dict = {"kind": self.kind, "value": self.value}

        if self.label is not None:
            data["label"] = self.label

        return data


@dataclass(frozen=True)
class ReferenceDocument:
    source: ReferenceSource
    content: str
    source_path: str = "AGENTS.md"
    version: str | None = None
    commit_sha: str | None = None

    def to_dict(self) -> dict:
        data: dict = {
            "source": self.source.to_dict(),
            "content": self.content,
            "source_path": self.source_path,
        }

        if self.version is not None:
            data["version"] = self.version

        if self.commit_sha is not None:
            data["commit_sha"] = self.commit_sha

        return data


@dataclass(frozen=True)
class ReferenceLoadResult:
    source: ReferenceSource
    document: ReferenceDocument | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        has_doc = self.document is not None
        has_err = self.error is not None

        if has_doc and has_err:
            raise ValueError("ReferenceLoadResult cannot have both document and error")

        if not has_doc and not has_err:
            raise ValueError("ReferenceLoadResult must have either document or error")

    @property
    def ok(self) -> bool:
        return self.document is not None

    def to_dict(self) -> dict:
        data: dict = {"source": self.source.to_dict()}

        if self.ok:
            data["document"] = self.document.to_dict()  # type: ignore[union-attr]
        else:
            data["error"] = self.error

        return data


@dataclass(frozen=True)
class ReferenceMetadata:
    agentskill_version: str
    sources: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agentskill_version": self.agentskill_version,
            "references": list(self.sources),
        }


def load_local_reference(source: ReferenceSource) -> ReferenceLoadResult:
    if source.kind != REFERENCE_KIND_LOCAL:
        return ReferenceLoadResult(
            source=source,
            error=f"unsupported local reference source kind: {source.kind}",
        )

    root = Path(source.value)

    if not root.exists():
        return ReferenceLoadResult(
            source=source,
            error=f"reference path does not exist: {source.value}",
        )

    if not root.is_dir():
        return ReferenceLoadResult(
            source=source,
            error=f"reference path is not a directory: {source.value}",
        )

    agents_path = root / REFERENCE_AGENTS_FILENAME

    if not agents_path.exists():
        return ReferenceLoadResult(
            source=source,
            error=f"AGENTS.md not found in reference repository: {source.value}",
        )

    content = read_text(agents_path)

    if not content:
        return ReferenceLoadResult(
            source=source,
            error=f"AGENTS.md is empty in reference repository: {source.value}",
        )

    if not content.strip():
        return ReferenceLoadResult(
            source=source,
            error=f"AGENTS.md is empty in reference repository: {source.value}",
        )

    doc = ReferenceDocument(
        source=source,
        content=content,
        source_path=REFERENCE_AGENTS_FILENAME,
    )

    return ReferenceLoadResult(source=source, document=doc)


def load_local_references(sources: list[ReferenceSource]) -> list[ReferenceLoadResult]:
    return [load_local_reference(s) for s in sources]
