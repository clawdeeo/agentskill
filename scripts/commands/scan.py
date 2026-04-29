#!/usr/bin/env python3
"""Walk the repository directory tree. Produce an annotated file inventory.

Outputs:
  - tree: flat list of all source files with metadata
  - summary: per-language file/line counts
  - read_order: suggested reading order (entry points first, then by size)

Usage:
    python scripts/scan.py <repo>
    python scripts/scan.py <repo> --lang python
    python scripts/scan.py <repo> --pretty
"""

import sys
from pathlib import Path

from common.fs import count_lines, validate_repo
from common.languages import language_for_path
from common.walk import walk_repo
from lib.cli_entrypoint import run_command_main

SKIP_EXTENSIONS: set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dylib",
    ".dll",
    ".class",
    ".jar",
    ".war",
    ".o",
    ".a",
    ".out",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".lock",
}

ENTRY_POINT_NAMES: set[str] = {
    "main",
    "cli",
    "app",
    "index",
    "server",
    "cmd",
    "__main__",
    "manage",
    "wsgi",
    "asgi",
    "run",
}


def _is_entry_point(stem: str) -> bool:
    return stem.lower() in ENTRY_POINT_NAMES


def scan(repo_path: str, lang_filter: str | None = None) -> dict:
    try:
        repo = validate_repo(repo_path)
    except ValueError as exc:
        return {"error": str(exc), "script": "scan"}

    tree: list[dict] = []
    depths: list[int] = []
    paths, _walk_stats = walk_repo(repo)

    for filepath in paths:
        ext = filepath.suffix.lower()

        if ext in SKIP_EXTENSIONS:
            continue

        spec = language_for_path(filepath)
        language = spec.id if spec else None

        if not language:
            continue

        if lang_filter and language != lang_filter:
            continue

        rel_path = str(filepath.relative_to(repo))

        try:
            size_bytes = filepath.stat().st_size
        except Exception:
            size_bytes = 0

        file_depth = len(filepath.relative_to(repo).parts)
        line_count = count_lines(filepath)
        depths.append(file_depth)

        tree.append(
            {
                "path": rel_path,
                "type": "file",
                "language": language,
                "size_bytes": size_bytes,
                "line_count": line_count,
                "depth": file_depth,
            }
        )

    by_language: dict[str, dict] = {}
    for entry in tree:
        lang = entry["language"]

        if lang not in by_language:
            by_language[lang] = {"file_count": 0, "total_lines": 0}

        by_language[lang]["file_count"] += 1
        by_language[lang]["total_lines"] += entry["line_count"]

    max_depth = max(depths, default=0)
    avg_depth = round(sum(depths) / len(depths), 1) if depths else 0.0

    summary = {
        "total_files": len(tree),
        "by_language": by_language,
        "max_depth": max_depth,
        "avg_depth": avg_depth,
    }

    entry_points = [e for e in tree if _is_entry_point(Path(e["path"]).stem)]
    rest = [e for e in tree if not _is_entry_point(Path(e["path"]).stem)]

    entry_points.sort(key=lambda e: -e["line_count"])
    rest.sort(key=lambda e: (-e["line_count"], e["path"]))

    read_order = [e["path"] for e in entry_points + rest]

    return {
        "tree": tree,
        "summary": summary,
        "read_order": read_order,
    }


def main(argv: list[str] | None = None) -> int:
    return run_command_main(
        argv=argv,
        description=__doc__,
        command_fn=scan,
        script_name="scan",
        supports_lang=True,
    )


if __name__ == "__main__":
    sys.exit(main())
