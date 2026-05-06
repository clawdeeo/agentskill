"""Shared output layout contract for generate and update flows.

Layout describes output packaging (single file, split, or multifile),
independent of profile which describes content density.
"""

SUPPORTED_OUTPUT_LAYOUTS = ("single", "split", "multifile")
DEFAULT_OUTPUT_LAYOUT = "single"


def validate_output_layout(value: str) -> str:
    """Normalize and validate an output layout name.

    Returns the normalized layout string on success.

    Raises ValueError for unsupported values.
    """
    normalized = value.strip().lower()

    if normalized not in SUPPORTED_OUTPUT_LAYOUTS:
        allowed = ", ".join(SUPPORTED_OUTPUT_LAYOUTS)
        raise ValueError(f"unsupported output layout: {value!r} (allowed: {allowed})")

    return normalized
