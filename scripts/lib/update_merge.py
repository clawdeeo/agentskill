"""Merge helpers for incremental AGENTS.md updates."""

from dataclasses import dataclass

from lib.agents_document import (
    AgentsDocument,
    AgentsSection,
    add_or_replace_section,
    normalize_section_name,
    parse_agents_document,
    serialize_agents_document,
)


@dataclass(frozen=True)
class MergeResult:
    """Structured merge output for future CLI reporting."""

    text: str
    updated_sections: list[str]
    preserved_sections: list[str]
    added_sections: list[str]
    removed_sections: list[str]
    forced: bool


def _normalize_names(names: list[str] | None) -> set[str]:
    if names is None:
        return set()

    return {normalize_section_name(name) for name in names}


def _normalize_regenerated_sections(
    regenerated_sections: dict[str, AgentsSection],
) -> dict[str, AgentsSection]:
    normalized_sections: dict[str, AgentsSection] = {}

    for raw_name, section in regenerated_sections.items():
        normalized_name = normalize_section_name(raw_name)

        if normalized_name in normalized_sections:
            raise ValueError(
                f"duplicate regenerated section after normalization: {raw_name}"
            )

        if section.normalized_name != normalized_name:
            raise ValueError(
                "regenerated section key does not match section heading: "
                f"{raw_name} != {section.heading_text}"
            )

        normalized_sections[normalized_name] = section

    return normalized_sections


def _resolve_target_sections(
    regenerated_sections: dict[str, AgentsSection],
    include_sections: list[str] | None,
    exclude_sections: list[str] | None,
) -> list[str]:
    included = _normalize_names(include_sections)
    excluded = _normalize_names(exclude_sections)
    overlap = included & excluded

    if overlap:
        names = ", ".join(sorted(overlap))
        raise ValueError(f"section names cannot be both included and excluded: {names}")

    targets = list(regenerated_sections)

    if included:
        targets = [name for name in targets if name in included]

    if excluded:
        targets = [name for name in targets if name not in excluded]

    return targets


def _merge_document(
    document: AgentsDocument,
    regenerated_sections: dict[str, AgentsSection],
    targets: list[str],
) -> tuple[AgentsDocument, list[str], list[str], list[str]]:
    existing_names = [section.normalized_name for section in document.sections]
    updated_sections: list[str] = []
    added_sections: list[str] = []
    merged = document

    for name in targets:
        section = regenerated_sections[name]

        if name in existing_names:
            updated_sections.append(name)
        else:
            added_sections.append(name)

        merged = add_or_replace_section(merged, section)

    preserved_sections = [
        name for name in existing_names if name not in set(updated_sections)
    ]

    return merged, updated_sections, preserved_sections, added_sections


def order_sections_for_force(
    regenerated_sections: dict[str, AgentsSection],
    preferred_order: list[str] | None = None,
) -> list[str]:
    """Return a stable ordering for force rebuilds."""
    ordered: list[str] = []
    seen: set[str] = set()

    for name in preferred_order or []:
        normalized_name = normalize_section_name(name)

        if normalized_name in regenerated_sections and normalized_name not in seen:
            ordered.append(normalized_name)
            seen.add(normalized_name)

    for name in sorted(regenerated_sections):
        if name not in seen:
            ordered.append(name)

    return ordered


def _build_force_document(
    regenerated_sections: dict[str, AgentsSection],
    targets: list[str],
) -> AgentsDocument:
    ordered_names = order_sections_for_force(
        {name: regenerated_sections[name] for name in targets}
    )
    return AgentsDocument(
        preamble="",
        sections=[regenerated_sections[name] for name in ordered_names],
    )


def merge_agents_document(
    existing_text: str | None,
    regenerated_sections: dict[str, AgentsSection],
    *,
    include_sections: list[str] | None = None,
    exclude_sections: list[str] | None = None,
    force: bool = False,
) -> MergeResult:
    """Merge regenerated sections into an existing AGENTS.md document."""
    normalized_sections = _normalize_regenerated_sections(regenerated_sections)

    targets = _resolve_target_sections(
        normalized_sections,
        include_sections,
        exclude_sections,
    )

    existing_document = parse_agents_document(existing_text or "")
    existing_names = [section.normalized_name for section in existing_document.sections]

    if force:
        document = _build_force_document(normalized_sections, targets)
        result_names = [section.normalized_name for section in document.sections]
        updated_sections = [name for name in result_names if name in existing_names]
        added_sections = [name for name in result_names if name not in existing_names]
        removed_sections = [name for name in existing_names if name not in result_names]

        return MergeResult(
            text=serialize_agents_document(document),
            updated_sections=updated_sections,
            preserved_sections=[],
            added_sections=added_sections,
            removed_sections=removed_sections,
            forced=True,
        )

    document, updated_sections, preserved_sections, added_sections = _merge_document(
        existing_document,
        normalized_sections,
        targets,
    )

    return MergeResult(
        text=serialize_agents_document(document),
        updated_sections=updated_sections,
        preserved_sections=preserved_sections,
        added_sections=added_sections,
        removed_sections=[],
        forced=False,
    )
