"""Reference repository data models for 0.5.0 reference loading."""

from dataclasses import dataclass, field
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

from common.fs import read_text

REFERENCE_KIND_LOCAL = "local"
REFERENCE_KIND_REMOTE = "remote"
SUPPORTED_REFERENCE_KINDS = {REFERENCE_KIND_LOCAL, REFERENCE_KIND_REMOTE}
REFERENCE_AGENTS_FILENAME = "AGENTS.md"
REMOTE_REFERENCE_GIT_TIMEOUT_SECONDS = 60


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


def _run_git(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        proc = run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=REMOTE_REFERENCE_GIT_TIMEOUT_SECONDS,
        )

        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 1, "", "git executable not found"
    except Exception as exc:
        return 1, "", str(exc)


def load_remote_reference(source: ReferenceSource) -> ReferenceLoadResult:
    if source.kind != REFERENCE_KIND_REMOTE:
        return ReferenceLoadResult(
            source=source,
            error=f"unsupported remote reference source kind: {source.kind}",
        )

    if not source.value:
        return ReferenceLoadResult(
            source=source,
            error="remote reference URL is empty",
        )

    with TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / "repo"

        rc, _, stderr = _run_git(
            [
                "git",
                "clone",
                "--depth",
                "1",
                source.value,
                str(clone_dir),
            ]
        )

        if rc != 0:
            return ReferenceLoadResult(
                source=source,
                error=f"failed to clone remote reference repository: {source.value}",
            )

        commit_sha: str | None = None
        rc, stdout, _ = _run_git(["git", "rev-parse", "HEAD"], cwd=clone_dir)

        if rc == 0 and stdout.strip():
            commit_sha = stdout.strip()

        agents_path = clone_dir / REFERENCE_AGENTS_FILENAME

        if not agents_path.exists():
            return ReferenceLoadResult(
                source=source,
                error=f"AGENTS.md not found in remote reference repository: {source.value}",
            )

        content = read_text(agents_path)

        if not content or not content.strip():
            return ReferenceLoadResult(
                source=source,
                error=f"AGENTS.md is empty in remote reference repository: {source.value}",
            )

        doc = ReferenceDocument(
            source=source,
            content=content,
            source_path=REFERENCE_AGENTS_FILENAME,
            commit_sha=commit_sha,
        )

        return ReferenceLoadResult(source=source, document=doc)


def load_remote_references(sources: list[ReferenceSource]) -> list[ReferenceLoadResult]:
    return [load_remote_reference(s) for s in sources]
