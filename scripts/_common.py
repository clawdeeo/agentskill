"""Shared utilities used across all analysis scripts.

Kept minimal: only things that are identical in three or more scripts
belong here. No logic beyond what every script already agrees on.
"""

SKIP_DIRS: set[str] = {
    "node_modules", "__pycache__", "dist", "build", "out",
    "target", "vendor", "third_party", ".eggs", "site-packages",
    "venv", ".venv", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov",
}


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")
