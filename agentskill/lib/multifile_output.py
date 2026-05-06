"""Multifile output helpers for per-section AGENTS generation."""

from pathlib import Path

from agentskill.lib.update_runner import SECTION_HEADINGS

SECTION_FILE_MAP: dict[str, str] = {
    "overview": "01_OVERVIEW.md",
    "repository structure": "02_REPOSITORY_STRUCTURE.md",
    "service map": "03_SERVICE_MAP.md",
    "cross-service boundaries": "04_CROSS_SERVICE_BOUNDARIES.md",
    "commands and workflows": "05_COMMANDS_AND_WORKFLOWS.md",
    "code formatting": "06_CODE_FORMATTING.md",
    "naming conventions": "07_NAMING_CONVENTIONS.md",
    "type annotations": "08_TYPE_ANNOTATIONS.md",
    "imports": "09_IMPORTS.md",
    "error handling": "10_ERROR_HANDLING.md",
    "comments and docstrings": "11_COMMENTS_AND_DOCSTRINGS.md",
    "testing": "12_TESTING.md",
    "git": "13_GIT.md",
    "dependencies and tooling": "14_DEPENDENCIES_AND_TOOLING.md",
    "red lines": "15_RED_LINES.md",
}

SECTION_DESCRIPTIONS: dict[str, str] = {
    "overview": "repository purpose, language set, architecture summary",
    "repository structure": "top-level layout and where code goes",
    "service map": "service boundaries and roots",
    "cross-service boundaries": "cross-service import rules and isolation",
    "commands and workflows": "install, check, test, and verification commands",
    "code formatting": "indentation, line length, whitespace, and multiline style",
    "naming conventions": "function, class, constant, and test naming rules",
    "type annotations": "annotation style, generics, and type-checker expectations",
    "imports": "import grouping, ordering, and per-line rules",
    "error handling": "validation errors, payload boundaries, and fallback behavior",
    "comments and docstrings": "docstring and inline comment expectations",
    "testing": "framework, test commands, naming, and coverage expectations",
    "git": "commit prefixes, merge strategy, and branch naming",
    "dependencies and tooling": "package metadata, Python floor, and detected tools",
    "red lines": "non-negotiable constraints and hard boundaries",
}

SECTION_DIR = ".agentskill"
BACKLINK_TEXT = "> Back to [`AGENTS.md`](../AGENTS.md)\n\n"


def section_file_path(primary_path: Path, section_name: str) -> Path:
    """Return the deterministic file path for a section file."""
    filename = SECTION_FILE_MAP[section_name]
    return primary_path.parent / SECTION_DIR / filename


def section_file_heading(section_name: str) -> str:
    """Return the markdown heading for a section file."""
    heading = SECTION_HEADINGS[section_name]
    number, _, title = heading.partition(" ")
    return f"# {number.strip()} {title.strip()}\n\n"


def build_section_file(
    section_name: str, body: str, include_backlink: bool = True
) -> str:
    """Build a section file with heading, optional backlink, and body."""
    parts: list[str] = []

    if include_backlink:
        parts.append(BACKLINK_TEXT)

    parts.append(section_file_heading(section_name))
    parts.append(body)

    return "".join(parts)


def build_root_index(
    primary_path: Path,
    section_names: list[str],
    overview_summary: str = "",
) -> str:
    """Build the compact root AGENTS.md for multifile layout."""
    parts: list[str] = []
    parts.append("# AGENTS.md\n\n")

    if overview_summary:
        parts.append(overview_summary.rstrip("\n") + "\n\n")

    parts.append(
        "This repository uses a multifile AGENTS layout. "
        "Load this file first, then open only the linked section documents you need.\n\n"
    )
    parts.append("## Section Index\n\n")

    for name in section_names:
        if name not in SECTION_FILE_MAP:
            continue

        heading = SECTION_HEADINGS[name]
        number, _, title = heading.partition(" ")
        filename = SECTION_FILE_MAP[name]
        description = SECTION_DESCRIPTIONS.get(name, "")
        rel_path = f"{SECTION_DIR}/{filename}"

        parts.append(
            f"- [{number.strip()} {title.strip()}](./{rel_path}) — {description}\n"
        )

    parts.append("\n")

    return "".join(parts)
