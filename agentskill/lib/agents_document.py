"""Helpers for parsing and updating sectioned AGENTS.md documents."""

import re
from dataclasses import dataclass

ATX_HEADING_RE = re.compile(r"^[ \t]{0,3}(?P<marks>#{1,6})(?:[ \t]+(?P<text>.*))?$")


def normalize_section_name(name: str) -> str:
    """Normalize a section name for deterministic lookup."""
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    normalized = re.sub(r"^\d+\.\s*", "", normalized)
    return normalized


@dataclass(frozen=True)
class AgentsSection:
    """A single heading-delimited AGENTS.md section."""

    heading_text: str
    normalized_name: str
    heading_level: int
    body: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "normalized_name",
            normalize_section_name(self.heading_text),
        )


@dataclass(frozen=True)
class AgentsDocument:
    """A parsed AGENTS.md document with ordered sections."""

    preamble: str
    sections: list[AgentsSection]


def build_section(
    heading_text: str,
    body: str,
    *,
    heading_level: int = 2,
) -> AgentsSection:
    """Build a section with normalized metadata."""
    return AgentsSection(
        heading_text=heading_text,
        normalized_name="",
        heading_level=heading_level,
        body=body,
    )


def _parse_heading(line: str) -> tuple[int, str] | None:
    raw_line = line.rstrip("\r\n")
    match = ATX_HEADING_RE.match(raw_line)

    if match is None:
        return None

    marks = match.group("marks")
    text = match.group("text") or ""
    return len(marks), text


def parse_agents_document(text: str) -> AgentsDocument:
    """Parse sectioned markdown into a document model."""
    preamble_lines: list[str] = []
    body_lines: list[str] = []
    sections: list[AgentsSection] = []
    current_heading: tuple[int, str] | None = None

    for line in text.splitlines(keepends=True):
        heading = _parse_heading(line)

        if heading is None:
            if current_heading is None:
                preamble_lines.append(line)
            else:
                body_lines.append(line)
            continue

        if (
            current_heading is None
            and not preamble_lines
            and heading[0] == 1
            and normalize_section_name(heading[1]) in {"agents", "agents.md"}
        ):
            preamble_lines.append(line)
            continue

        if current_heading is not None:
            sections.append(
                build_section(
                    current_heading[1],
                    "".join(body_lines),
                    heading_level=current_heading[0],
                )
            )

        current_heading = heading
        body_lines = []

    if current_heading is None:
        return AgentsDocument(preamble="".join(preamble_lines), sections=[])

    sections.append(
        build_section(
            current_heading[1],
            "".join(body_lines),
            heading_level=current_heading[0],
        )
    )

    return AgentsDocument(preamble="".join(preamble_lines), sections=sections)


def serialize_agents_document(document: AgentsDocument) -> str:
    """Serialize a parsed document back to markdown."""
    parts = [document.preamble]

    for section in document.sections:
        parts.append(f"{'#' * section.heading_level} {section.heading_text}\n")
        body = section.body

        if not body:
            parts.append("\n")
            continue

        if not body.startswith("\n"):
            parts.append("\n")

        parts.append(body)

        if not body.endswith("\n"):
            parts.append("\n")

        if not body.endswith("\n\n"):
            parts.append("\n")

    return "".join(parts)


def get_section(document: AgentsDocument, name: str) -> AgentsSection | None:
    """Return the first section matching the normalized name."""
    normalized_name = normalize_section_name(name)

    for section in document.sections:
        if section.normalized_name == normalized_name:
            return section

    return None


def replace_section(document: AgentsDocument, section: AgentsSection) -> AgentsDocument:
    """Replace the first matching section and leave the rest unchanged."""
    sections = list(document.sections)

    for index, existing in enumerate(sections):
        if existing.normalized_name == section.normalized_name:
            sections[index] = section
            return AgentsDocument(preamble=document.preamble, sections=sections)

    return document


def add_or_replace_section(
    document: AgentsDocument, section: AgentsSection
) -> AgentsDocument:
    """Replace the first matching section or append when absent."""
    updated = replace_section(document, section)

    if updated is not document:
        return updated

    return AgentsDocument(
        preamble=document.preamble,
        sections=[*document.sections, section],
    )
