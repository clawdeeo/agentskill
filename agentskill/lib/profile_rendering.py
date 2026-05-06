"""Profile-aware section body assembly for generate and update flows."""

from dataclasses import dataclass


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
