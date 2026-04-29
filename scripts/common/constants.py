"""Shared constants for repository walking and test discovery."""

MAX_FILES_TO_PARSE = 10_000
MAX_FILE_BYTES = 1_000_000

MAKEFILE_NAMES = ("Makefile", "makefile", "GNUmakefile")
TOP_LEVEL_TEST_DIRS = {"tests", "test", "__tests__", "spec"}
TEST_STRUCTURE_SOURCE_ROOTS = ("src", "lib", "pkg")

SKIP_DIRS: set[str] = {
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "out",
    "target",
    "vendor",
    "third_party",
    ".eggs",
    "site-packages",
    "venv",
    ".venv",
    ".tox",
    ".nox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".next",
    ".nuxt",
    "coverage",
}


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")
