"""Shared reference normalization and loading helpers for CLI flows."""

from pathlib import Path

from agentskill.lib.reference_initialization import successful_reference_documents
from agentskill.lib.references import (
    REFERENCE_KIND_LOCAL,
    REFERENCE_KIND_REMOTE,
    ReferenceDocument,
    ReferenceLoadResult,
    ReferenceSource,
    load_local_reference,
    load_remote_reference,
)

REMOTE_REFERENCE_PREFIXES = (
    "http://",
    "https://",
    "ssh://",
    "git@",
)


def _reference_kind(value: str) -> str:
    if value.startswith(REMOTE_REFERENCE_PREFIXES):
        return REFERENCE_KIND_REMOTE

    return REFERENCE_KIND_LOCAL


def _reference_identity(source: ReferenceSource) -> tuple[str, str]:
    if source.kind == REFERENCE_KIND_LOCAL:
        return source.kind, str(Path(source.value).resolve())

    return source.kind, source.value


def normalize_reference_sources(
    references: list[str] | None,
) -> list[ReferenceSource]:
    if not references:
        return []

    sources = [
        ReferenceSource(kind=_reference_kind(reference), value=reference)
        for reference in references
    ]

    seen: set[tuple[str, str]] = set()

    for source in sources:
        identity = _reference_identity(source)

        if identity in seen:
            raise ValueError(f"duplicate reference source: {source.value}")

        seen.add(identity)

    return sources


def load_reference_results(references: list[str] | None) -> list[ReferenceLoadResult]:
    results: list[ReferenceLoadResult] = []

    for source in normalize_reference_sources(references):
        if source.kind == REFERENCE_KIND_REMOTE:
            results.append(load_remote_reference(source))
        else:
            results.append(load_local_reference(source))

    return results


def load_reference_documents(references: list[str] | None) -> list[ReferenceDocument]:
    results = load_reference_results(references)
    errors = [result.error for result in results if result.error is not None]

    if errors:
        raise ValueError("; ".join(errors))

    return successful_reference_documents(results)
