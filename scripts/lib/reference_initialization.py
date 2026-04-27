"""Empty-project initialization from references and generated reference metadata."""

import json
from dataclasses import dataclass, field

from lib.reference_adaptation import ReferenceAdaptationResult, adapt_references
from lib.reference_questions import ReferenceQuestion, generate_reference_questions
from lib.references import ReferenceDocument, ReferenceLoadResult, ReferenceMetadata

AGENTSKILL_VERSION = "0.5.0"


def successful_reference_documents(
    results: list[ReferenceLoadResult],
) -> list[ReferenceDocument]:
    return [r.document for r in results if r.ok and r.document is not None]


def is_empty_target(target_analysis: dict) -> bool:
    scan = target_analysis.get("scan", {})
    summary = scan.get("summary", {})
    total_files = summary.get("total_files", 0)

    if total_files > 0:
        return False

    tree = scan.get("tree", [])

    if tree:
        return False

    has_config = bool(target_analysis.get("config"))
    has_git = bool(target_analysis.get("git"))
    has_tests = bool(target_analysis.get("tests"))

    return not (has_config or has_git or has_tests)


def build_reference_metadata(
    documents: list[ReferenceDocument],
    agentskill_version: str,
) -> ReferenceMetadata:
    sources: list[dict] = []

    for doc in documents:
        entry: dict = {
            "kind": doc.source.kind,
            "value": doc.source.value,
            "source_path": doc.source_path,
        }

        if doc.commit_sha is not None:
            entry["commit_sha"] = doc.commit_sha

        if doc.source.label is not None:
            entry["label"] = doc.source.label

        sources.append(entry)

    return ReferenceMetadata(agentskill_version=agentskill_version, sources=sources)


def render_reference_metadata_block(metadata: ReferenceMetadata) -> str:
    data = metadata.to_dict()
    json_str = json.dumps(data, indent=2)

    return f"<!-- agentskill-metadata\n{json_str}\n-->"


@dataclass(frozen=True)
class ReferenceInitializationResult:
    is_reference_derived: bool
    adapted_references: list[ReferenceAdaptationResult]
    questions: list[ReferenceQuestion]
    metadata: ReferenceMetadata
    usable_reference_count: int = 0
    warnings: list[str] = field(default_factory=list)


def initialize_from_references(
    target_analysis: dict,
    documents: list[ReferenceDocument],
    *,
    agentskill_version: str = AGENTSKILL_VERSION,
) -> ReferenceInitializationResult:
    is_empty = is_empty_target(target_analysis)
    metadata = build_reference_metadata(documents, agentskill_version)
    warnings: list[str] = []

    adapted: list[ReferenceAdaptationResult] = []

    if documents:
        adapted = adapt_references(documents, target_analysis)
    else:
        warnings.append("no reference documents provided")

    questions = generate_reference_questions(adapted, target_analysis=target_analysis)

    if is_empty and not any(
        c.status == "applicable" for r in adapted for c in r.conventions
    ):
        warnings.append("empty target with no applicable reference conventions")

    return ReferenceInitializationResult(
        is_reference_derived=is_empty,
        adapted_references=adapted,
        questions=questions,
        metadata=metadata,
        usable_reference_count=len(documents),
        warnings=warnings,
    )
