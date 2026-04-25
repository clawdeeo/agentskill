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

import json
import os
import sys
from pathlib import Path

SKIP_DIRS: set[str] = {
    "node_modules", "__pycache__", "dist", "build", "out",
    "target", "vendor", "third_party", ".eggs", "site-packages",
    "venv", ".venv", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov", ".next", ".nuxt", "coverage",
}

SKIP_EXTENSIONS: set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dylib", ".dll",
    ".class", ".jar", ".war",
    ".o", ".a", ".out",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz",
    ".lock",
}

EXTENSIONS: dict[str, str] = {
    ".py":   "python",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".mjs":  "javascript",
    ".go":   "go",
    ".rs":   "rust",
    ".rb":   "ruby",
    ".java": "java",
    ".kt":   "kotlin",
    ".swift": "swift",
    ".cpp":  "cpp",
    ".cc":   "cpp",
    ".cxx":  "cpp",
    ".c":    "c",
    ".h":    "c",
    ".cs":   "csharp",
    ".sh":   "bash",
    ".bash": "bash",
}

ENTRY_POINT_NAMES: set[str] = {
    "main", "cli", "app", "index", "server", "cmd",
    "__main__", "manage", "wsgi", "asgi", "run",
}


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def _count_lines(path: Path) -> int:
    try:
        with open(path, "rb") as f:
            return f.read().count(b"\n")
    except Exception:
        return 0


def _is_entry_point(stem: str) -> bool:
    return stem.lower() in ENTRY_POINT_NAMES


def scan(repo_path: str, lang_filter: str | None = None) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "scan"}
    if not repo.is_dir():
        return {"error": f"not a directory: {repo_path}", "script": "scan"}

    tree: list[dict] = []
    depths: list[int] = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if not _should_skip_dir(d))
        rel_dir = Path(dirpath).relative_to(repo)
        depth = len(rel_dir.parts)

        for filename in sorted(files):
            filepath = Path(dirpath) / filename
            ext = filepath.suffix.lower()

            if ext in SKIP_EXTENSIONS:
                continue

            language = EXTENSIONS.get(ext)
            if not language:
                continue
            if lang_filter and language != lang_filter:
                continue

            rel_path = str(filepath.relative_to(repo))
            try:
                size_bytes = filepath.stat().st_size
            except Exception:
                size_bytes = 0

            line_count = _count_lines(filepath)
            file_depth = depth + 1
            depths.append(file_depth)

            tree.append({
                "path": rel_path,
                "type": "file",
                "language": language,
                "size_bytes": size_bytes,
                "line_count": line_count,
                "depth": file_depth,
            })

    # Summary
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

    # Read order: entry points first, then by line count descending per language
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
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="Path to repository")
    parser.add_argument("--lang", help="Filter to a single language")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output")
    args = parser.parse_args(argv)

    try:
        result = scan(args.repo, args.lang)
    except Exception as exc:
        result = {"error": str(exc), "script": "scan"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
