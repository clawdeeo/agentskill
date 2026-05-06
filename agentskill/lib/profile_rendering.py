"""Profile-aware section body assembly for generate and update flows."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RenderedSectionBody:
    """Core and expanded detail for a single section.

    ``core`` is always emitted. ``expanded`` is appended only when the
    selected output profile is ``comprehensive``.
    """

    core: str
    expanded: str = ""


def combine_section_body(profile: str, body: RenderedSectionBody) -> str:
    """Return the final section text for the given profile.

    For ``concise`` only ``core`` is used.  For ``comprehensive`` the
    ``expanded`` text is appended.  The function is deliberately small
    so that callers never need to know about profile internals.
    """
    if profile == "concise":
        return body.core

    return body.core + body.expanded


COMPANION_SUFFIX = ".reference.md"
DOCUMENT_TITLE = "# AGENTS.md\n\n"
COMPANION_TITLE = "# AGENTS Reference\n\n"


def companion_path(primary_path: Path) -> Path:
    """Return the deterministic companion file path for a split primary.

    The companion is placed beside the primary with ``.reference.md``
    inserted before the final ``.md`` extension.  If the primary has no
    ``.md`` extension, the companion suffix is appended directly.
    """
    name = primary_path.name

    if name.lower().endswith(".md"):
        stem = name[:-3]
        companion_name = stem + COMPANION_SUFFIX
    else:
        companion_name = name + COMPANION_SUFFIX

    return primary_path.parent / companion_name


def companion_relative_link(primary_path: Path) -> str:
    """Return the relative link text pointing from primary to companion."""
    return (
        f"[{companion_path(primary_path).name}](./{companion_path(primary_path).name})"
    )


def inject_split_link(markdown: str, primary_path: Path) -> str:
    """Insert a reference link near the top of the primary markdown.

    The link is inserted immediately after the title heading if the
    document starts with ``# AGENTS.md``, otherwise it is prepended.
    """
    link = f"> Extended reference: {companion_relative_link(primary_path)}\n"

    if markdown.startswith(DOCUMENT_TITLE):
        return DOCUMENT_TITLE + link + "\n" + markdown.removeprefix(DOCUMENT_TITLE)

    return link + "\n" + markdown


def build_companion_document(comprehensive_markdown: str) -> str:
    """Build the companion document from the comprehensive markdown.

    Replaces the ``# AGENTS.md`` title with ``# AGENTS Reference`` and
    adds a short note that this file is the extended companion.
    """
    opening = "> Extended reference document for the main AGENTS.md.\n\n"

    if comprehensive_markdown.startswith(DOCUMENT_TITLE):
        return (
            opening
            + COMPANION_TITLE
            + comprehensive_markdown.removeprefix(DOCUMENT_TITLE)
        )

    return opening + comprehensive_markdown
