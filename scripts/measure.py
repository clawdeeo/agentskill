#!/usr/bin/env python3
"""Exact formatting metrics. No estimation. Count every line.

Measures indentation, line lengths, blank line patterns, trailing newlines,
and trailing whitespace across all source files in the repository.

Usage:
    python scripts/measure.py <repo>
    python scripts/measure.py <repo> --lang python
    python scripts/measure.py <repo> --pretty
"""

import ast
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median

MAX_SMALL_INDENT = 8
MIN_FILES_FOR_LINE_LENGTH = 5
MAX_FILES_REPORTED = 10

SKIP_DIRS: set[str] = {
    "node_modules", "__pycache__", "dist", "build", "out",
    "target", "vendor", "third_party", ".eggs", "site-packages",
    "venv", ".venv", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov", ".next", ".nuxt", "coverage",
}

EXTENSIONS: dict[str, str] = {
    ".py":    "python",
    ".ts":    "typescript",
    ".tsx":   "typescript",
    ".js":    "javascript",
    ".jsx":   "javascript",
    ".mjs":   "javascript",
    ".go":    "go",
    ".rs":    "rust",
    ".rb":    "ruby",
    ".java":  "java",
    ".kt":    "kotlin",
    ".swift": "swift",
    ".cpp":   "cpp",
    ".cc":    "cpp",
    ".cxx":   "cpp",
    ".c":     "c",
    ".cs":    "csharp",
}

TOP_LEVEL_DEF_RE: dict[str, re.Pattern] = {
    "typescript": re.compile(r"^(export\s+)?(default\s+)?(async\s+)?function\s+\w+|^(export\s+)?(abstract\s+)?class\s+\w+|^(export\s+)?const\s+\w+\s*=\s*(async\s+)?\("),
    "javascript": re.compile(r"^(export\s+)?(default\s+)?(async\s+)?function\s+\w+|^(export\s+)?(abstract\s+)?class\s+\w+|^(export\s+)?const\s+\w+\s*=\s*(async\s+)?\("),
    "go":         re.compile(r"^func\s+"),
    "rust":       re.compile(r"^(pub\s+)?(async\s+)?fn\s+\w+|^(pub\s+)?struct\s+\w+|^(pub\s+)?enum\s+\w+|^(pub\s+)?trait\s+\w+|^impl\s+"),
    "ruby":       re.compile(r"^def\s+\w+|^class\s+\w+|^module\s+\w+"),
    "java":       re.compile(r"^\s*(public|private|protected|static|final|abstract)\s+.*\{$"),
}

METHOD_DEF_RE: dict[str, re.Pattern] = {
    "typescript": re.compile(r"^  (public|private|protected|static|async|abstract|\w+)\s+\w+\s*\("),
    "javascript": re.compile(r"^  (async\s+)?\w+\s*\("),
    "go":         re.compile(r"^\tfunc\s+"),
    "ruby":       re.compile(r"^  def\s+"),
}


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def _collect_files(repo: Path, lang_filter: str | None) -> dict[str, list[Path]]:
    by_lang: dict[str, list[Path]] = {}
    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fn in files:
            ext = Path(fn).suffix.lower()
            lang = EXTENSIONS.get(ext)
            if not lang:
                continue
            if lang_filter and lang != lang_filter:
                continue
            by_lang.setdefault(lang, []).append(Path(dirpath) / fn)
    return by_lang


# ---------------------------------------------------------------------------
# Indentation
# ---------------------------------------------------------------------------

def _measure_indentation(lines: list[str]) -> dict:
    space_sizes: list[int] = []
    has_spaces = False
    has_tabs = False

    for line in lines:
        if not line.rstrip():
            continue
        if line.startswith("\t"):
            has_tabs = True
        elif line.startswith(" "):
            has_spaces = True
            indent = len(line) - len(line.lstrip(" "))
            if indent > 0:
                space_sizes.append(indent)

    if has_tabs and not has_spaces:
        return {"unit": "tabs", "size": 1}
    if not has_spaces:
        return {"unit": "unknown", "size": 0}
    if not space_sizes:
        return {"unit": "spaces", "size": 4}

    small = [s for s in space_sizes if s <= MAX_SMALL_INDENT]
    if not small:
        return {"unit": "spaces", "size": 4}

    cnt = Counter(small)
    candidates = sorted(cnt.keys())
    unit = candidates[0]
    for s in [2, 4]:
        if cnt[s] > cnt.get(unit, 0) * 0.5:
            unit = s
            break

    return {"unit": "spaces", "size": unit}


def _consensus_indentation(
    votes: list[dict],
    tab_files: list[str],
    mixed_files: list[str],
) -> dict:
    """Fold per-file indentation votes into a single consensus dict."""
    units = Counter(v["unit"] for v in votes if v["unit"] != "unknown")
    sizes = Counter(v["size"] for v in votes if v["unit"] != "unknown" and v["size"] > 0)
    return {
        "unit":        units.most_common(1)[0][0] if units else "spaces",
        "size":        sizes.most_common(1)[0][0] if sizes else 4,
        "tab_files":   tab_files[:MAX_FILES_REPORTED],
        "mixed_files": mixed_files[:MAX_FILES_REPORTED],
    }


# ---------------------------------------------------------------------------
# Line lengths
# ---------------------------------------------------------------------------

def _percentile(sorted_data: list[int], p: int) -> int:
    if not sorted_data:
        return 0
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def _measure_line_lengths(all_lengths: list[int]) -> dict:
    if len(all_lengths) < MIN_FILES_FOR_LINE_LENGTH:
        return {}
    s = sorted(all_lengths)
    return {
        "p50": _percentile(s, 50),
        "p75": _percentile(s, 75),
        "p95": _percentile(s, 95),
        "p99": _percentile(s, 99),
        "max": s[-1],
    }


# ---------------------------------------------------------------------------
# Blank line helpers
# ---------------------------------------------------------------------------

def _count_blanks_before_line(lines: list[str], i: int) -> int:
    count = 0
    j = i - 1
    while j >= 0 and not lines[j].strip():
        count += 1
        j -= 1
    return count


def _dist_summary(data: list[int]) -> dict:
    if not data:
        return {}
    cnt = Counter(data)
    mode = cnt.most_common(1)[0][0]
    distribution = {str(k): v for k, v in sorted(cnt.items())}
    return {"mode": mode, "distribution": distribution}


# ---------------------------------------------------------------------------
# Python blank line passes
# ---------------------------------------------------------------------------

def _blanks_between_top_level(tree: ast.AST, lines: list[str]) -> list[int]:
    """Count blank lines before each top-level def/class."""
    top_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.col_offset == 0
    ]
    top_nodes.sort(key=lambda n: n.lineno)
    return [
        _count_blanks_before_line(lines, n.lineno - 1)
        for n in top_nodes
        if n.lineno > 1
    ]


def _blanks_between_methods(tree: ast.AST, lines: list[str]) -> tuple[list[int], list[int]]:
    """Count blank lines between class methods and after class declaration.

    Returns (between_methods, after_class_decl).
    """
    between: list[int] = []
    after_decl: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [
            n for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not methods:
            continue

        after_decl.append(_count_blanks_before_line(lines, methods[0].lineno - 1))
        for m in methods[1:]:
            between.append(_count_blanks_before_line(lines, m.lineno - 1))

    return between, after_decl


def _blanks_after_imports(tree: ast.AST, lines: list[str]) -> list[int]:
    """Count blank lines after the last import statement."""
    import_lines = [
        n.lineno for n in ast.walk(tree)
        if isinstance(n, (ast.Import, ast.ImportFrom))
    ]
    if not import_lines:
        return []

    last_import = max(import_lines)
    if last_import >= len(lines):
        return []

    count = 0
    j = last_import  # 1-indexed → 0-indexed
    while j < len(lines) and not lines[j].strip():
        count += 1
        j += 1

    return [count]


def _measure_blank_lines_python(files: list[Path]) -> dict:
    """Use ast module for Python blank line analysis."""
    between_top_level: list[int] = []
    between_methods:   list[int] = []
    after_class_decl:  list[int] = []
    after_imports:     list[int] = []

    for fp in files:
        try:
            source = fp.read_text(errors="ignore")
            lines = source.splitlines()
            tree = ast.parse(source)
        except Exception:
            continue

        between_top_level.extend(_blanks_between_top_level(tree, lines))

        methods, decls = _blanks_between_methods(tree, lines)
        between_methods.extend(methods)
        after_class_decl.extend(decls)

        after_imports.extend(_blanks_after_imports(tree, lines))

    return {
        "between_top_level_defs":   _dist_summary(between_top_level),
        "between_methods":          _dist_summary(between_methods),
        "after_class_declaration":  _dist_summary(after_class_decl),
        "after_imports":            _dist_summary(after_imports),
    }


def _measure_blank_lines_generic(files: list[Path], lang: str) -> dict:
    """Regex-based blank line analysis for non-Python languages."""
    pattern        = TOP_LEVEL_DEF_RE.get(lang)
    method_pattern = METHOD_DEF_RE.get(lang)

    between_top_level: list[int] = []
    between_methods:   list[int] = []

    for fp in files:
        try:
            lines = fp.read_text(errors="ignore").splitlines()
        except Exception:
            continue

        if pattern:
            for i, line in enumerate(lines):
                if pattern.match(line) and i > 0:
                    between_top_level.append(_count_blanks_before_line(lines, i))

        if method_pattern:
            for i, line in enumerate(lines):
                if method_pattern.match(line) and i > 0:
                    between_methods.append(_count_blanks_before_line(lines, i))

    result: dict = {}
    if between_top_level:
        result["between_top_level_defs"] = _dist_summary(between_top_level)
    if between_methods:
        result["between_methods"] = _dist_summary(between_methods)
    return result


# ---------------------------------------------------------------------------
# Per-file metrics accumulation
# ---------------------------------------------------------------------------

def _file_metrics(fp: Path) -> dict | None:
    """Return raw per-file measurements, or None if the file can't be read."""
    try:
        content = fp.read_text(errors="ignore")
    except Exception:
        return None

    raw_lines = content.split("\n")
    lines = raw_lines[:-1] if content.endswith("\n") else raw_lines

    indent      = _measure_indentation(lines)
    has_tabs    = any(l.startswith("\t") for l in lines if l.strip())
    has_spaces  = any(l.startswith(" ")  for l in lines if l.strip())
    line_lengths = [len(l.rstrip("\n\r")) for l in lines if l.strip()]
    trailing_newline = content.endswith("\n")
    has_trailing_ws  = any(re.search(r"\s+$", l) for l in lines if l.strip())

    return {
        "indent":          indent,
        "has_tabs":        has_tabs,
        "has_spaces":      has_spaces,
        "line_lengths":    line_lengths,
        "trailing_newline": trailing_newline,
        "has_trailing_ws": has_trailing_ws,
        "path":            str(fp),
    }


# ---------------------------------------------------------------------------
# Language-level aggregation
# ---------------------------------------------------------------------------

def _measure_lang(lang: str, files: list[Path]) -> dict:
    all_line_lengths: list[int] = []
    indent_votes:     list[dict] = []
    tab_files:        list[str] = []
    mixed_files:      list[str] = []
    trailing_newline_present = 0
    trailing_newline_absent  = 0
    files_with_trailing_ws   = 0

    for fp in files:
        m = _file_metrics(fp)
        if m is None:
            continue

        indent_votes.append(m["indent"])
        all_line_lengths.extend(m["line_lengths"])

        if m["trailing_newline"]:
            trailing_newline_present += 1
        else:
            trailing_newline_absent += 1

        if m["has_trailing_ws"]:
            files_with_trailing_ws += 1

        if m["has_tabs"] and m["has_spaces"]:
            mixed_files.append(m["path"])
        elif m["has_tabs"]:
            tab_files.append(m["path"])

    if lang == "python":
        blank_lines = _measure_blank_lines_python(files)
    else:
        blank_lines = _measure_blank_lines_generic(files, lang)

    return {
        "indentation":  _consensus_indentation(indent_votes, tab_files, mixed_files),
        "line_length":  _measure_line_lengths(all_line_lengths),
        "blank_lines":  blank_lines,
        "trailing_newline": {
            "present": trailing_newline_present,
            "absent":  trailing_newline_absent,
        },
        "trailing_whitespace": {
            "files_with_trailing_ws": files_with_trailing_ws,
        },
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def measure(repo_path: str, lang_filter: str | None = None) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "measure"}

    by_lang = _collect_files(repo, lang_filter)
    result: dict = {}

    for lang, files in by_lang.items():
        if not files:
            continue
        try:
            result[lang] = _measure_lang(lang, files)
        except Exception as exc:
            result[lang] = {"error": str(exc)}

    return result


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
        result = measure(args.repo, args.lang)
    except Exception as exc:
        result = {"error": str(exc), "script": "measure"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
