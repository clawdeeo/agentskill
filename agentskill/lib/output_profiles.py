"""Shared output profile contract for generate and update flows."""

SUPPORTED_OUTPUT_PROFILES = ("concise", "comprehensive", "split")
DEFAULT_OUTPUT_PROFILE = "concise"


def validate_output_profile(value: str) -> str:
    """Normalize and validate an output profile name.

    Returns the normalized profile string on success.

    Raises ValueError for unsupported values.
    """
    normalized = value.strip().lower()

    if normalized not in SUPPORTED_OUTPUT_PROFILES:
        allowed = ", ".join(SUPPORTED_OUTPUT_PROFILES)
        raise ValueError(f"unsupported output profile: {value!r} (allowed: {allowed})")

    return normalized
